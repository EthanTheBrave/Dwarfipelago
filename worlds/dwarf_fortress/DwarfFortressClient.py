"""
DwarfFortressClient - bridges a running Dwarf Fortress (via DFHack's remote API)
and an Archipelago multiworld server (via WebSocket).

Run with:
    python DwarfFortressClient.py --server archipelago.gg:PORT --name YourSlotName

DFHack remote API listens on 127.0.0.1:5000 by default.
"""

import asyncio
import copy
import json
import logging
import os
import socket
import struct
import argparse
import subprocess
import sys
import threading
import time
from typing import Any, Optional
from CommonClient import CommonContext, server_loop, ClientCommandProcessor, logger
from NetUtils import ClientStatus
from Utils import async_start, format_SI_prefix

_STEAM_CANDIDATES: list[str] = [
    # Windows - 32-bit Steam
    r"C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress\Dwarf Fortress.exe",
    # Windows - 64-bit Steam
    r"C:\Program Files\Steam\steamapps\common\Dwarf Fortress\Dwarf Fortress.exe",
    # Linux - default Steam library
    os.path.expanduser("~/.steam/steam/steamapps/common/Dwarf Fortress/dfhack"),
    # Linux - flatpak Steam
    os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam"
                       "/steamapps/common/Dwarf Fortress/dfhack"),
    # macOS - Steam
    os.path.expanduser("~/Library/Application Support/Steam"
                       "/steamapps/common/Dwarf Fortress/dfhack"),
]

# ── DFHack Remote API ─────────────────────────────────────────────────────────

DFHACK_HOST = "127.0.0.1"
DFHACK_PORT = 5000

# DFHack remote API handshake - magic (8 bytes) + version int32 LE (4 bytes) = 12 bytes total.
# The client sends the request magic+version; the server replies with reply magic+version.
# If only the 8-byte magic is sent, DFHack waits for the remaining 4 bytes and the
# connection hangs until our recv() times out - hence "DFHack not reachable: timed out".
_DFHACK_VERSION       = struct.pack("<i", 1)
DFHACK_MAGIC_REQUEST  = b"DFHack?\n" + _DFHACK_VERSION   # 12 bytes
DFHACK_MAGIC_REPLY    = b"DFHack!\n" + _DFHACK_VERSION   # 12 bytes

# DFHack RPC reply / special IDs (carried in the message header's id field).
# Source: DFHack RemoteClient.h - enum DFHackReplyCode : int16_t
# See https://docs.dfhack.org/en/stable/docs/dev/Remote.html
RPC_METHOD_BIND  =  0   # BindMethod request - always method id 0
RPC_REPLY_RESULT = -1   # successful result; body is the reply protobuf
RPC_REPLY_FAIL   = -2   # call failed; body is CoreErrorInfo
RPC_REPLY_TEXT   = -3   # TextNotification (console output emitted mid-call)
RPC_REQUEST_QUIT = -4   # graceful disconnect
# RPCMessageHeader: int16_t id (2 bytes) + 2 bytes alignment pad + int32_t size (4 bytes) = 8 bytes.
# The C++ compiler inserts 2 bytes of padding after the int16_t so the int32_t is 4-byte aligned.
# DFHack does not guarantee the padding bytes are zero, so we must parse by offset, not as two int32s.
RPC_HEADER_SIZE  =  8

# ── Minimal protobuf wire encoding / decoding ─────────────────────────────────
# We only need CoreBindRequest/Reply and CoreRunCommandRequest, so we hand-roll
# the tiny subset rather than pulling in generated proto classes.

def _pb_varint(value: int) -> bytes:
    """Encode a non-negative integer as a protobuf varint."""
    out = bytearray()
    while True:
        towrite = value & 0x7F
        value >>= 7
        if value:
            out.append(towrite | 0x80)
        else:
            out.append(towrite)
            break
    return bytes(out)


def _pb_string(field: int, value: str) -> bytes:
    """Encode a protobuf string field (wire type 2 = length-delimited)."""
    enc = value.encode("utf-8")
    return _pb_varint((field << 3) | 2) + _pb_varint(len(enc)) + enc


def _pb_decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    result, shift = 0, 0
    while pos < len(data):
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80):
            break
    return result, pos


def _pb_decode(data: bytes) -> dict[int, list]:
    """
    Shallow-decode a protobuf message.
    Returns {field_number: [value, ...]} where value is int (varint)
    or bytes (length-delimited / nested message).
    """
    fields: dict[int, list] = {}
    pos = 0
    while pos < len(data):
        tag, pos = _pb_decode_varint(data, pos)
        field_num, wire_type = tag >> 3, tag & 0x07
        if wire_type == 0:          # varint
            val, pos = _pb_decode_varint(data, pos)
        elif wire_type == 2:        # length-delimited
            length, pos = _pb_decode_varint(data, pos)
            val = data[pos:pos + length]
            pos += length
        else:
            break                   # unsupported wire type; stop parsing
        fields.setdefault(field_num, []).append(val)
    return fields


def _extract_text_notification(body: bytes) -> str:
    """
    Extract plain text from a CoreTextNotification protobuf body.

    Actual DFHack proto (dfhack.proto):
      CoreTextNotification { repeated CoreTextFragment fragments = 1; }
      CoreTextFragment     { required string text = 1;
                             optional DFHackColorType color = 2; }

    Two levels only: CoreTextNotification → CoreTextFragment → text string.
    """
    parts = []
    for frag_bytes in _pb_decode(body).get(1, []):   # CoreTextNotification.fragments
        if not isinstance(frag_bytes, bytes):
            continue
        for s in _pb_decode(frag_bytes).get(1, []):  # CoreTextFragment.text
            if isinstance(s, bytes):
                parts.append(s.decode("utf-8", errors="replace"))
    return "".join(parts)

def _get_df_executable() -> Optional[str]:
    """Return the DF executable path from settings, or fall back to Steam defaults."""
    # 1. Try AP settings (host.yaml).
    try:
        from settings import get_settings
        path = str(get_settings().dwarf_fortress_options.game_path)
        if os.path.isfile(path):
            return path
    except Exception:
        pass

    # 2. Try common Steam install locations.
    for path in _STEAM_CANDIDATES:
        if os.path.isfile(path):
            return path

    return None


# ── World gen preset install ───────────────────────────────────────────────────
# Moved here from the old DFHack console script (dwarfipelago-worldgen-install.lua)
# so players install the preset from the AP client with "/dfinstall" instead of
# running a console command inside DF.

WORLD_GEN_PRESET_TITLE = "DwarfipelagoWorld"

WORLD_GEN_PRESET = (
    "\n"
    "[WORLD_GEN]\n"
    "\t[TITLE:DwarfipelagoWorld]\n"
    "\t[DIM:65:65]\n"
    "\t[EMBARK_POINTS:1504]\n"
    "\t[END_YEAR:120]\n"
    "\t[BEAST_END_YEAR:100:80]\n"
    "\t[REVEAL_ALL_HISTORY:1]\n"
    "\t[CULL_HISTORICAL_FIGURES:0]\n"
    "\t[ELEVATION:1:400:202:202]\n"
    "\t[RAINFALL:0:100:101:101]\n"
    "\t[TEMPERATURE:25:75:101:101]\n"
    "\t[DRAINAGE:0:100:101:101]\n"
    "\t[VOLCANISM:0:100:101:101]\n"
    "\t[SAVAGERY:0:100:101:101]\n"
    "\t[ELEVATION_FREQUENCY:1:1:1:1:1:1]\n"
    "\t[RAIN_FREQUENCY:1:1:1:1:1:1]\n"
    "\t[DRAINAGE_FREQUENCY:1:1:1:1:1:1]\n"
    "\t[TEMPERATURE_FREQUENCY:1:1:1:1:1:1]\n"
    "\t[SAVAGERY_FREQUENCY:1:1:1:1:1:1]\n"
    "\t[VOLCANISM_FREQUENCY:1:1:1:1:1:1]\n"
    "\t[POLE:NORTH_AND_OR_SOUTH]\n"
    "\t[MINERAL_SCARCITY:100]\n"
    "\t[MEGABEAST_CAP:4]\n"
    "\t[SEMIMEGABEAST_CAP:9]\n"
    "\t[TITAN_NUMBER:3]\n"
    "\t[TITAN_ATTACK_TRIGGER:3:0:3]\n"
    "\t[DEMON_NUMBER:22]\n"
    "\t[NIGHT_TROLL_NUMBER:11]\n"
    "\t[BOGEYMAN_NUMBER:11]\n"
    "\t[NIGHTMARE_NUMBER:11]\n"
    "\t[VAMPIRE_NUMBER:11]\n"
    "\t[WEREBEAST_NUMBER:11]\n"
    "\t[WEREBEAST_ATTACK_TRIGGER:2:2:2]\n"
    "\t[SECRET_NUMBER:22]\n"
    "\t[REGIONAL_INTERACTION_NUMBER:22]\n"
    "\t[DISTURBANCE_INTERACTION_NUMBER:22]\n"
    "\t[EVIL_CLOUD_NUMBER:11]\n"
    "\t[EVIL_RAIN_NUMBER:11]\n"
    "\t[GENERATE_DIVINE_MATERIALS:1]\n"
    "\t[GENERATE_MYTHICAL_MATERIALS:1]\n"
    "\t[ALLOW_MYTHICAL_HEALING:1]\n"
    "\t[ALLOW_DIVINATION:1]\n"
    "\t[ALLOW_DEMONIC_EXPERIMENTS:1]\n"
    "\t[ALLOW_NECROMANCER_EXPERIMENTS:1]\n"
    "\t[ALLOW_NECROMANCER_LIEUTENANTS:1]\n"
    "\t[ALLOW_NECROMANCER_GHOULS:1]\n"
    "\t[ALLOW_NECROMANCER_SUMMONS:1]\n"
    "\t[GOOD_SQ_COUNTS:6:63:127]\n"
    "\t[EVIL_SQ_COUNTS:6:63:127]\n"
    "\t[PEAK_NUMBER_MIN:3]\n"
    "\t[PARTIAL_OCEAN_EDGE_MIN:1]\n"
    "\t[COMPLETE_OCEAN_EDGE_MIN:0]\n"
    "\t[VOLCANO_MIN:5]\n"
    "\t[REGION_COUNTS:SWAMP:66:0:0]\n"
    "\t[REGION_COUNTS:DESERT:66:0:0]\n"
    "\t[REGION_COUNTS:FOREST:264:2:2]\n"
    "\t[REGION_COUNTS:MOUNTAINS:528:0:0]\n"
    "\t[REGION_COUNTS:OCEAN:528:0:0]\n"
    "\t[REGION_COUNTS:GLACIER:0:0:0]\n"
    "\t[REGION_COUNTS:TUNDRA:0:0:0]\n"
    "\t[REGION_COUNTS:GRASSLAND:264:2:2]\n"
    "\t[REGION_COUNTS:HILLS:528:0:0]\n"
    "\t[EROSION_CYCLE_COUNT:250]\n"
    "\t[RIVER_MINS:25:25]\n"
    "\t[PERIODICALLY_ERODE_EXTREMES:1]\n"
    "\t[OROGRAPHIC_PRECIPITATION:1]\n"
    "\t[SUBREGION_MAX:2750]\n"
    "\t[CAVERN_LAYER_COUNT:3]\n"
    "\t[CAVERN_LAYER_OPENNESS_MIN:0]\n"
    "\t[CAVERN_LAYER_OPENNESS_MAX:100]\n"
    "\t[CAVERN_LAYER_PASSAGE_DENSITY_MIN:0]\n"
    "\t[CAVERN_LAYER_PASSAGE_DENSITY_MAX:100]\n"
    "\t[CAVERN_LAYER_WATER_MIN:0]\n"
    "\t[CAVERN_LAYER_WATER_MAX:100]\n"
    "\t[HAVE_BOTTOM_LAYER_1:1]\n"
    "\t[HAVE_BOTTOM_LAYER_2:1]\n"
    "\t[LEVELS_ABOVE_GROUND:15]\n"
    "\t[LEVELS_ABOVE_LAYER_1:5]\n"
    "\t[LEVELS_ABOVE_LAYER_2:1]\n"
    "\t[LEVELS_ABOVE_LAYER_3:1]\n"
    "\t[LEVELS_ABOVE_LAYER_4:1]\n"
    "\t[LEVELS_ABOVE_LAYER_5:2]\n"
    "\t[LEVELS_AT_BOTTOM:1]\n"
    "\t[CAVE_MIN_SIZE:5]\n"
    "\t[CAVE_MAX_SIZE:25]\n"
    "\t[MOUNTAIN_CAVE_MIN:6]\n"
    "\t[NON_MOUNTAIN_CAVE_MIN:12]\n"
    "\t[MYTHICAL_SITE_NUM:200]\n"
    "\t[ALL_CAVES_VISIBLE:0]\n"
    "\t[SHOW_EMBARK_TUNNEL:2]\n"
    "\t[TOTAL_CIV_NUMBER:20]\n"
    "\t[TOTAL_CIV_POPULATION:15000]\n"
    "\t[SITE_CAP:400]\n"
    "\t[PLAYABLE_CIVILIZATION_REQUIRED:1]\n"
    "\t[ELEVATION_RANGES:528:1056:528]\n"
    "\t[RAIN_RANGES:264:528:264]\n"
    "\t[DRAINAGE_RANGES:264:528:264]\n"
    "\t[SAVAGERY_RANGES:264:528:264]\n"
    "\t[VOLCANISM_RANGES:264:528:264]\n"
)


def _find_worldgen_prefs_path() -> Optional[str]:
    """
    Locate the DF prefs/world_gen.txt file across platforms.

    Steam DF on Windows redirects user prefs to %APPDATA%\\Bay 12 Games\\Dwarf
    Fortress\\ rather than the install directory. Linux/macOS keep prefs
    alongside the install, so we derive it from the DF executable location.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        return os.path.join(appdata, "Bay 12 Games", "Dwarf Fortress", "prefs", "world_gen.txt")

    exe = _get_df_executable()
    if not exe:
        return None
    return os.path.join(os.path.dirname(exe), "prefs", "world_gen.txt")


def install_worldgen_preset() -> str:
    """
    Append the Dwarfipelago world-gen preset to the player's world_gen.txt if it
    isn't already present. Safe to call repeatedly. Returns a status message
    for printing to the AP client console.
    """
    prefs_path = _find_worldgen_prefs_path()
    if not prefs_path:
        return ("Could not locate prefs/world_gen.txt - set 'game_path' in host.yaml "
                 "to your Dwarf Fortress executable and try again.")

    existing = ""
    if os.path.isfile(prefs_path):
        with open(prefs_path, "r", encoding="utf-8") as f:
            existing = f.read()

    if WORLD_GEN_PRESET_TITLE in existing:
        return f"World gen preset is already installed in {prefs_path}"

    os.makedirs(os.path.dirname(prefs_path), exist_ok=True)
    with open(prefs_path, "a", encoding="utf-8") as f:
        f.write(WORLD_GEN_PRESET)

    return (f"World gen preset installed to {prefs_path}\n"
            f"Restart Dwarf Fortress for 'DwarfipelagoWorld' to appear in the preset list.")


# ── DFHack connection ─────────────────────────────────────────────────────────

class DFHackConnection:
    """
    Minimal DFHack remote API client.

    Implements only what Dwarfipelago needs:
    - run_command: execute a DFHack console command (including inline Lua)
    - pop_pending_checks: atomically read and clear the check queue
    - deliver_item: call the Lua item handler for a received AP item
    """

    def __init__(self, host: str = DFHACK_HOST, port: int = DFHACK_PORT):
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        # Serializes a full request→reply exchange on the shared socket. Without
        # it, two run_command calls (e.g. one in an executor thread and one
        # direct) can interleave their sends/reads, crossing replies and
        # desyncing the byte stream ("BindMethod failed: reply_id=<garbage>").
        self._lock = threading.RLock()

    def connect(self) -> bool:
        try:
            sock = socket.create_connection((self.host, self.port), timeout=5)
            sock.sendall(DFHACK_MAGIC_REQUEST)
            buf = bytearray()
            needed = len(DFHACK_MAGIC_REPLY)
            while len(buf) < needed:
                chunk = sock.recv(needed - len(buf))
                if not chunk:
                    raise ConnectionError("DFHack closed connection during handshake")
                buf.extend(chunk)
            reply = bytes(buf)
            if reply != DFHACK_MAGIC_REPLY:
                logger.error(f"DFHack handshake failed: {reply!r}")
                sock.close()
                return False
            # Handshake done - widen the timeout for normal RPC calls.
            # The 5-second connect timeout is too short for commands like
            # 'dwarfipelago start' that register hooks and take longer to return.
            sock.settimeout(30)
            self._sock = sock
            logger.info(f"Connected to DFHack at {self.host}:{self.port}")
            return True
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            logger.warning(f"DFHack not reachable: {e}")
            return False

    def disconnect(self):
        # Take the lock so we never close the socket while another thread is
        # mid-read/write on it (which raises WinError 10038 / WSAENOTSOCK).
        # RLock makes this safe to call from inside a locked run_command too.
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
            # Clear the cached method ID so BindMethod is re-issued next connection.
            self.__dict__.pop("_run_cmd_id", None)

    def is_connected(self) -> bool:
        return self._sock is not None

    # ── Wire-level helpers ────────────────────────────────────────────────────

    def _recv_exactly(self, n: int) -> bytes:
        """Block until exactly n bytes have been received from the socket."""
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("DFHack closed the connection mid-message")
            buf.extend(chunk)
        return bytes(buf)

    def _send_rpc(self, method_id: int, body: bytes) -> None:
        # RPCMessageHeader: int16_t id + int16_t pad(=0) + int32_t size = 8 bytes.
        # Explicitly zero the 2-byte alignment pad so DFHack sees a clean header.
        self._sock.sendall(struct.pack("<hhi", method_id, 0, len(body)) + body)

    def _recv_rpc(self) -> tuple[int, bytes]:
        # RPCMessageHeader is 8 bytes: int16_t id @ offset 0, int32_t size @ offset 4.
        # The 2 bytes at offset 2 are alignment padding and may be non-zero garbage
        # from DFHack's stack - extract fields by offset rather than treating the
        # header as two int32s.
        raw = self._recv_exactly(RPC_HEADER_SIZE)
        reply_id = struct.unpack_from("<h", raw, 0)[0]   # int16_t at offset 0
        size     = struct.unpack_from("<i", raw, 4)[0]   # int32_t at offset 4
        body = self._recv_exactly(size) if size > 0 else b""
        return reply_id, body

    def _bind_method(self, method: str, input_msg: str = "", output_msg: str = "",
                     plugin: str = "") -> int:
        """
        Call BindMethod (always RPC id 0) to obtain the assigned integer ID
        for a named method. Returns -1 on failure.

        Sends:   CoreBindRequest  { method(1), input_msg(2), output_msg(3), plugin(4)? }
        Expects: CoreBindReply    { assigned_id(1) }

        CoreBindRequest.input_msg and output_msg are proto2 *required* fields -
        omitting them causes DFHack to reject the request with "could not decode
        input args".  Pass the fully-qualified proto type names, e.g.:
            input_msg  = "dfproto.CoreRunCommandRequest"
            output_msg = "dfproto.EmptyMessage"

        Core methods (RunCommand, GetVersion, …) use an empty plugin string.
        Plugin methods set plugin to the plugin name, e.g. "rename".
        The method name is always the bare name ("RunCommand"), NOT "Core.RunCommand".
        """
        body = _pb_string(1, method)
        if input_msg:
            body += _pb_string(2, input_msg)
        if output_msg:
            body += _pb_string(3, output_msg)
        if plugin:
            body += _pb_string(4, plugin)
        self._send_rpc(RPC_METHOD_BIND, body)
        reply_id, data = self._recv_rpc()
        if reply_id == RPC_REPLY_RESULT:
            ids = _pb_decode(data).get(1, [-1])
            return ids[0] if ids else -1
        # A non-RESULT reply here means the stream is misaligned (e.g. leftover
        # bytes from a prior desynced command). Drop the socket so the caller
        # reconnects and re-handshakes cleanly instead of compounding the desync.
        logger.error(f"BindMethod failed for {method!r}: reply_id={reply_id}, data={data!r} "
                     f"- resetting connection")
        self.disconnect()
        return -1

    # ── Public API ────────────────────────────────────────────────────────────

    def run_command(self, command: str, *args: str) -> Optional[str]:
        """
        Execute a DFHack console command via the Core.RunCommand RPC.

        `command` is the DFHack command name (e.g. "lua"); any additional
        positional arguments are passed as RunCommand arguments.

        Returns the concatenated console output (from TextNotification packets),
        or None on failure.

        Example:
            conn.run_command("lua", 'print(df.global.plotinfo.tasks.wealth)')
        """
        if not self._sock:
            return None
        # Human-readable description of this call for error logs. Long arguments
        # (e.g. inline Lua) are truncated so the log stays readable.
        def _fmt(s: str, limit: int = 300) -> str:
            return s if len(s) <= limit else s[:limit] + f"...(+{len(s) - limit} chars)"
        call_desc = " ".join([command, *(_fmt(a) for a in args)])
        # Hold the lock for the entire request→reply exchange so no other call
        # can read or write the socket in between (which would cross replies and
        # desync the stream).
        with self._lock:
            # Re-check inside the lock: a concurrent disconnect() may have closed
            # the socket between the early check above and acquiring the lock.
            if not self._sock:
                return None
            try:
                if not hasattr(self, "_run_cmd_id"):
                    # CoreBindRequest.input_msg and output_msg are proto2 *required*
                    # fields - must pass the fully-qualified proto type names.
                    self._run_cmd_id = self._bind_method(
                        "RunCommand",
                        "dfproto.CoreRunCommandRequest",
                        "dfproto.EmptyMessage",
                    )
                    if self._run_cmd_id < 0:
                        logger.error(f"Failed to bind RunCommand | call: {call_desc!r}")
                        return None

                # Encode CoreRunCommandRequest { command(1), arguments(2 repeated) }
                body = _pb_string(1, command)
                for arg in args:
                    body += _pb_string(2, arg)
                self._send_rpc(self._run_cmd_id, body)

                # Drain TextNotification packets until we receive a Result or Error.
                # Valid reply codes during a command are only TEXT/RESULT/FAIL.
                # Anything else means the byte stream is misaligned (a desync) -
                # we must NOT just break (that leaves the real terminator in the
                # buffer for the next call to misread as a header). Instead we
                # tear down the socket so the next call reconnects and re-handshakes
                # from a clean state.
                output_parts: list[str] = []
                while True:
                    reply_id, data = self._recv_rpc()
                    if reply_id == RPC_REPLY_TEXT:
                        text = _extract_text_notification(data)
                        text = text.replace("\n", "")
                        output_parts.append(text)
                    elif reply_id == RPC_REPLY_RESULT:
                        break
                    elif reply_id == RPC_REPLY_FAIL:
                        logger.warning(f"DFHack RunCommand failed (id={reply_id}): {data!r} "
                                       f"| call: {call_desc!r}")
                        return None
                    else:
                        logger.error(f"DFHack RunCommand: unexpected reply id={reply_id} "
                                     f"(stream desynced) - resetting connection "
                                     f"| call: {call_desc!r}")
                        self.disconnect()
                        return None

                return "".join(output_parts)

            except Exception as e:
                logger.warning(f"DFHack run_command error: {e} | call: {call_desc!r}")
                self.disconnect()
                return None

    def pop_pending_checks(self) -> list[int]:
        """
        Atomically read and clear the pending-checks queue written by the Lua mod.
        The mod stores the queue as a JSON array in world data under
        "dwarfipelago/pending_checks". Returns a list of AP location IDs.
        """
        lua = (
            "(function()"
            " local q = dfhack.persistent.getWorldDataString"
            '("dwarfipelago/pending_checks") or "[]";'
            ' dfhack.persistent.saveWorldDataString("dwarfipelago/pending_checks", "[]");'
            " print(q)"
            " end)()"
        )
        output = self.run_command("lua", lua)
        if not output:
            return []
        try:
            ids = json.loads(output.strip())
            return [int(x) for x in ids] if isinstance(ids, list) else []
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse pending checks - {e!r} - raw: {output!r}")
            return []

    def deliver_item(self, item_name: str):
        """Deliver a received AP item to the fortress by calling the Lua item handler."""
        safe_name = item_name.replace("\\", "\\\\").replace('"', '\\"')
        result = self.run_command(
            "lua",
            f'reqscript("internal/dwarfipelago/items").receive("{safe_name}")',
        )
        if result is None:
            logger.warning(f"deliver_item: RPC returned None for {item_name!r} - connection lost?")
        else:
            logger.debug(f"Delivered item to fortress: {item_name!r} (lua output: {result.strip()!r})")


# ── Archipelago Client ────────────────────────────────────────────────────────

class DwarfFortressCommandProcessor(ClientCommandProcessor):
    """Adds Dwarfipelago-specific client console commands."""

    def _cmd_dfdebug(self, state: str = ""):
        """Toggle Dwarfipelago debug logging (verbose craft counts, item delivery,
        index/restore details). Usage: /dfdebug [on|off]"""
        state = state.strip().lower()
        if state in ("on", "true", "1"):
            self.ctx.debug_mode = True
        elif state in ("off", "false", "0"):
            self.ctx.debug_mode = False
        else:
            self.ctx.debug_mode = not self.ctx.debug_mode
        logger.info(f"Dwarfipelago debug logging {'ON' if self.ctx.debug_mode else 'OFF'}")

    def _cmd_energy_link(self):
        """Print the status of the energy link."""
        self.output(f"Energy Link: {self.ctx.energy_link_status}")

    def _cmd_dfinstall(self):
        """Install the Dwarfipelago world generation preset into your Dwarf
        Fortress prefs/world_gen.txt. Run this once before generating a new
        world. Usage: /dfinstall"""
        for line in install_worldgen_preset().splitlines():
            self.output(line)

    # def _cmd_send_energy_link(self, amount: str = ""):
    #     """Send energy to test energy link. usage: /send_energy_link <amount>"""
    #     difference = int(amount)
    #     if difference <= 0:
    #         self.ctx.last_deplete = time.time()
    #         async_start(self.ctx.send_msgs([{
    #             "cmd": "Set", "key": self.ctx.energylink_key, "operations":
    #                 [{"operation": "add", "value": difference},
    #                 {"operation": "max", "value": 0}],
    #             "last_deplete": self.ctx.last_deplete
    #         }]))
    #         logger.debug(f"EnergyLink: Used {format_SI_prefix(difference)}*")
    #     else:
    #         async_start(self.ctx.send_msgs([{
    #             "cmd": "Set", "key": self.ctx.energylink_key, "operations":
    #                 [{"operation": "add", "value": difference}]
    #         }]))
    #         logger.debug(f"EnergyLink: Sent {format_SI_prefix(difference)}*")
        


class DwarfFortressContext(CommonContext):
    """
    Archipelago client context for Dwarf Fortress.

    Connects to both:
    - The DFHack remote API (TCP 5000) to read fortress state
    - The Archipelago server (WebSocket) to send/receive multiworld messages
    """

    game = "Dwarf Fortress"
    items_handling = 0b111  # receive all items (local + remote + starting inventory)
    command_processor = DwarfFortressCommandProcessor

    def __init__(self, server_address: str, password: Optional[str] = None):
        super().__init__(server_address, password)
        self.dfhack = DFHackConnection()
        self.dfhack_task = False
        self.debug_mode = False          # verbose diagnostics off by default; /dfdebug toggles
        self._poll_interval = 5.0        # seconds between fortress state polls
        self._received_index = 0         # last applied item index
        self._received_index_loaded = False  # restored from world data this connection?
        self._slot_data_synced = False   # Loaded the correct saved world
        self._goal_complete = False
        self._deathlink_enabled = False  # set from slot_data; gates sending + the DeathLink tag
        self._deathlink_threshold = 5    # dwarves (or %) per DeathLink (overridden by slot data)
        self._deathlink_percentage = False  # treat threshold as % of population
        self._pending_recv_deathlinks = 0  # incoming DeathLink bounces waiting to be applied
        self._mod_started = False        # True once dwarfipelago/main start has succeeded
        self._world_loaded = False       # True while DF has an active world loaded
        self._crafting_locations = {}    # Dict of all crafting locations
        self._craftsanity_max_value = 0     # max items to produce
        self._craftsanity_threshold = 0     # crafting thresholds
        self._completed_crafting_locations = [] #completed locations so we don't keep sending
        self._completed_locations_loaded = False  # True once the AP Get reply has populated the list
        self.seed = 0                    # your "identity"
        self.version = 0                 # apworld version
        self.energy_link_enabled = False # energy link
        self.last_deplete = 0            # energy link
        self.last_energy = 0             # energy link
        self.current_energy = 0          # energy link
        self._skillsanity_enabled = 0    # Skillsanity
        self._skill_locations = {}       # required locations
        self._skill_max_level = 15       # max level
        self._skill_behaviour = 0        # 0 = don't touch levels 1 = lower to next check
        self._shop_scout_sent = False    # sent LocationScouts for shop slots this AP session
        self._shop_last_sig = None       # last shop table written to Lua (skip redundant writes)
        self._is_reembark = False        # True during re-embark item re-delivery
        self._custom_caves_enabled = False   # from slot_data; gates cave generation + discovery
        self._discovered_caves: set[int] = set()  # cave indices already sent as location checks

    def debug(self, msg: str):
        """Log only when debug mode is enabled (toggle with /dfdebug)."""
        if self.debug_mode:
            logger.info(f"[debug] {msg}")

    # ── DFHack polling ────────────────────────────────────────────────────────

    async def dfhack_poll_loop(self):
        """
        Main loop: connect to DFHack, poll for new checks, apply received items.
        Reconnects automatically if DFHack drops.

        All persistent-storage operations (saveWorldDataString / getWorldDataString)
        require an active loaded world. We check dfhack.isWorldLoaded() at the top
        of every cycle and skip the cycle entirely when DF is at the main menu.
        """
        while True:
            if not self.dfhack.is_connected():
                connected = await asyncio.get_event_loop().run_in_executor(
                    None, self.dfhack.connect
                )
                if not connected:
                    await asyncio.sleep(10)
                    continue

            try:
                # ── Map-loaded guard ──────────────────────────────────────────
                # saveWorldDataString / getWorldDataString require an active map.
                # isMapLoaded() is stricter than isWorldLoaded() - it returns true
                # only once fortress/adventure mode is fully live, not during world
                # generation or loading screens.
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.dfhack.run_command(
                        "lua", "print(dfhack.isMapLoaded() and '1' or '0')"
                    ),
                )
                world_loaded = bool(result and result.strip() == "1")
                if not world_loaded:
                    if self._world_loaded:
                        # Transition: player returned to the main menu / world gen.
                        self._world_loaded = False
                        self._mod_started = False
                        self._slot_data_synced = False
                        self._received_index_loaded = False
                        self._completed_locations_loaded = False
                        self._shop_last_sig = None  # force a re-write to the next loaded save
                        logger.info("Map unloaded - AP operations paused until a save is loaded")
                    await asyncio.sleep(self._poll_interval)
                    continue

                if not self._world_loaded:
                    self._world_loaded = True
                    logger.info("Map loaded - resuming AP operations")
                # ── Auto-start mod ────────────────────────────────────────────
                # 'dwarfipelago start' is safe to call on an already-running mod;
                # it just re-registers hooks. We do it once per world load.
                if not self._mod_started:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.dfhack.run_command("dwarfipelago", "start"),
                    )
                    self._mod_started = True
                    logger.info("Auto-started dwarfipelago mod")
                # ── Fortress operations (map guaranteed loaded) ───────────────
                await self._sync_slot_data()
                if self._slot_data_synced:
                    # DeathLink, goal, and cave checks are safe to run at any time.
                    await self._apply_received_deathlinks()
                    await self._check_deathlink_send()
                    await self._check_goal_complete()
                    await self._check_cave_discoveries()

                    # Location checks and item delivery are held until the trade
                    # depot is established - either auto-placed by the mod or
                    # manually built by the player.
                    depot_result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.dfhack.run_command(
                            "lua",
                            'print(dfhack.persistent.getWorldDataString'
                            '("dwarfipelago/depot_built") or "")',
                        ),
                    )
                    depot_ready = bool(depot_result and depot_result.strip() == "1")
                    if depot_ready:
                        await self._process_new_checks()
                        await self._crafting_location_checks()
                        await self._skill_location_checks()
                        await self._apply_pending_items()
                        await self.update_energy()
                        await self.new_energy()
                        await self._check_caravan_request()
                        await self._sync_shop()
                        await self._check_shop_purchase()
                    else:
                        logger.debug("Trade depot not yet established - holding checks and item delivery")

            except Exception as e:
                # Log the full traceback to the AP client so failures are
                # actionable rather than a one-line summary.
                logger.error(f"DFHack poll error: {e!r} - disconnecting and retrying", exc_info=True)
                self.dfhack.disconnect()
                self._slot_data_synced = False
                self._mod_started = False
                self._world_loaded = False
                self._received_index_loaded = False

            await asyncio.sleep(self._poll_interval)

    async def _process_new_checks(self):
        """Read new location checks from the Lua mod and report them to AP."""
        location_ids = await asyncio.get_event_loop().run_in_executor(
            None, self.dfhack.pop_pending_checks
        )
        if location_ids:
            self.debug(f"New checks: {location_ids}")
            await self.send_msgs([{
                "cmd": "LocationChecks",
                "locations": location_ids,
            }])

    _IMMIGRATION_WAVE_ID = 37370631  # BASE_ID + 631
    _TRAP_FLAG           = 0b100     # ItemClassification.trap bit

    async def _apply_pending_items(self):
        """Apply any received AP items that haven't been delivered yet."""
        # self.items_received is populated by CommonClient when the server sends ReceivedItems.
        # We apply items in order starting from self._received_index.

        # Restore the last-applied index from world data once per connection.
        # Without this, _received_index resets to 0 on every client restart and
        # every received item is re-delivered - which re-increments counter-based
        # progression locks (Immigration Wave, Merchant's Coffer, Military
        # Training) and re-spawns trade goods. The index is persisted per-save in
        # DFHack world data, so it is the authoritative count of what's applied.
        if not self._received_index_loaded:
            raw = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.dfhack.run_command(
                    "lua",
                    'print(dfhack.persistent.getWorldDataString'
                    '("dwarfipelago/received_index") or "0")',
                ),
            )
            try:
                self._received_index = int(raw.strip()) if raw and raw.strip() not in ("", "nil") else 0
            except (ValueError, AttributeError):
                self._received_index = 0
            self._received_index_loaded = True
            self.debug(f"Restored received item index from world data: {self._received_index}")

            # Detect re-embark: fresh fortress (index=0) but AP has already sent items.
            # The map-unload handler resets _received_index_loaded whenever the player
            # returns to the menu, so this branch runs once per fortress load.
            if self._received_index == 0 and len(self.items_received) > 0:
                wave_count = sum(
                    1 for item in self.items_received
                    if item.item == self._IMMIGRATION_WAVE_ID
                )
                logger.info(
                    f"[Dwarfipelago] Re-embark detected — restoring {len(self.items_received)} item(s), "
                    f"{wave_count} immigration wave(s), traps skipped"
                )
                # Pre-set the immigration wave counter to its final value so that
                # individual wave deliveries don't increment it (they check reembark_mode).
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda wc=wave_count: self.dfhack.run_command(
                        "lua",
                        f'dfhack.persistent.saveWorldDataString("dwarfipelago/unlock/immigration_waves", "{wc}");'
                        f'dfhack.persistent.saveWorldDataString("dwarfipelago/reembark_mode", "1")',
                    ),
                )
                self._is_reembark = True

        pending = len(self.items_received) - self._received_index
        if pending > 0:
            self.debug(f"Applying {pending} pending item(s) starting at index {self._received_index}")

        skipped_traps = 0
        for i in range(self._received_index, len(self.items_received)):
            network_item = self.items_received[i]

            if network_item.item == 37370530: # Cave Fisher Silk - always skip (junk filler)
                self._received_index = i + 1
                self.dfhack.run_command(
                    "lua",
                    f'dfhack.persistent.saveWorldDataString("dwarfipelago/received_index", "{i + 1}")',
                )
                continue

            # During re-embark, skip all trap-classified items so a recovering fortress
            # isn't immediately hit with goblin ambushes and vermin infestations.
            if self._is_reembark and (network_item.flags & self._TRAP_FLAG):
                skipped_traps += 1
                self._received_index = i + 1
                self.dfhack.run_command(
                    "lua",
                    f'dfhack.persistent.saveWorldDataString("dwarfipelago/received_index", "{i + 1}")',
                )
                continue

            # Resolve numeric item ID → human-readable name.
            # The Lookup API changed between AP versions; try each approach in order.
            item_name: str
            try:
                if hasattr(self, "item_names") and hasattr(self.item_names, "lookup_in_game"):
                    item_name = self.item_names.lookup_in_game(network_item.item)
                elif hasattr(self, "item_names"):
                    item_name = self.item_names.get(network_item.item, str(network_item.item))
                else:
                    item_name = str(network_item.item)
            except Exception as e:
                logger.warning(f"Item name lookup failed for id {network_item.item}: {e}")
                item_name = str(network_item.item)

            self.debug(f"Delivering item [{i}]: id={network_item.item} → name={item_name!r}")

            await asyncio.get_event_loop().run_in_executor(
                None, self.dfhack.deliver_item, item_name
            )
            self._received_index = i + 1
            # Persist the index so we don't re-deliver on restart.
            self.dfhack.run_command(
                "lua",
                f'dfhack.persistent.saveWorldDataString("dwarfipelago/received_index",'
                f' "{self._received_index}")',
            )

        # After all items have been delivered on re-embark, spawn one consolidated
        # batch of immigrants and clear the reembark_mode flag in Lua.
        if self._is_reembark and self._received_index >= len(self.items_received):
            wave_count = sum(
                1 for item in self.items_received
                if item.item == self._IMMIGRATION_WAVE_ID
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda wc=wave_count: self.dfhack.run_command(
                    "lua",
                    f'reqscript("internal/dwarfipelago/items").reembark_batch_spawn({wc})',
                ),
            )
            self._is_reembark = False
            logger.info(
                f"[Dwarfipelago] Re-embark recovery complete"
                + (f" — {skipped_traps} trap(s) skipped" if skipped_traps else "")
            )

    async def _sync_slot_data(self):
        """
        Write AP slot data (goal type + targets) to DFHack persistent storage
        so the Lua mod can read the goal settings without an RPC round-trip.
        Runs once per DFHack connection; resets when DFHack disconnects.
        """
        if self._slot_data_synced:
            return
        slot_data = getattr(self, "slot_data", {})
        if not slot_data:
            return  # not yet connected to AP, or no slot data
        goal         = slot_data.get("goal", 0)
        wealth_goal  = slot_data.get("wealth_goal_amount", 100000)
        pop_goal     = slot_data.get("population_goal_amount", 300)
        dl_threshold   = slot_data.get("deathlink_threshold", 5)
        dl_percentage  = slot_data.get("deathlink_percentage", 0)
        self.seed         = slot_data.get("seed", 0)
        self._crafting_locations = slot_data.get("crafting_locations")
        self._craftsanity_max_value = slot_data.get("craftsanity_max_amount")
        self._craftsanity_threshold = slot_data.get("craftsanity_threshold")
        craftsanity_enabled = slot_data.get("craftsanity_enabled") # 0 off, 1 on, 2 storage
        self.version = slot_data.get("version")
        materials_enabled = slot_data.get("craftsanity_materials")
        king_remains_amt = slot_data.get("remains_great_king")
        craftingpermits = slot_data.get("crafting_permits")
        mining_depth = slot_data.get("mining_depth")
        self._skillsanity_enabled = slot_data.get("skillsanity_enabled")
        self._skill_locations = slot_data.get("skillsanity_locations")
        self._skill_max_level = slot_data.get("skillsanity_max_level")
        self._skill_behaviour = slot_data.get("skillsanity_behaviour")
        current_seed = self.dfhack.run_command("lua", f'print(dfhack.persistent.getWorldDataString("dwarfipelago/seed"))')
        current_seed = (current_seed or "").strip()
        # A blank/"nil" stored seed means this world has no AP identity yet (fresh,
        # or cleared via "dwarfipelago resetseed"), so adopt this slot's seed.
        seed_is_fresh = current_seed in ("nil", "", "None")
        self._deathlink_threshold  = int(dl_threshold)
        self._deathlink_percentage = bool(int(dl_percentage))
        if seed_is_fresh or current_seed == str(self.seed):
            script_version = (self.dfhack.run_command("lua", f'print(dfhack.persistent.getWorldDataString("dwarfipelago/version"))') or "").strip()
            if self.version == script_version:
                if seed_is_fresh:
                    def write():
                        self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/goal", "{goal}")')
                        self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/wealth_goal", "{wealth_goal}")')
                        self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/pop_goal", "{pop_goal}")')
                        self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/king_remains_goal", "{king_remains_amt}")')
                        self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/crafting_permits", "{craftingpermits}")')
                        self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/deathlink", "{1 if self._deathlink_enabled else 0}")')
                        self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/deathlink_threshold", "{dl_threshold}")')
                        self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/deathlink_percentage", "{int(dl_percentage)}")')
                        self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/seed", "{self.seed}")')
                        self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/custom_caves", "{1 if self._custom_caves_enabled else 0}")')
                    write()
                    self.init_crafting_locations()
                    self.init_skill_locations()
                # Energy link flag - Lua reads this to know the feature is on.
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/energy_enabled", "{1 if self.energy_link_enabled else 0}")')
                # Mining Depth flag - Lua reads this to know the feature is on.
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/mining_depth", "{1 if mining_depth else 0}")')
                # Always re-sync these flags so Lua uses the correct key format
                # even on reconnects or if the initial write was interrupted.
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/craftsanity_enabled", "{craftsanity_enabled}")')
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/craftsanity_materials", "{materials_enabled}")')
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/crafting_permits", "{craftingpermits}")')
                #skillsanity
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/skillsanity_enabled", "{self._skillsanity_enabled}")')
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/skillsanity_max_level", "{self._skill_max_level}")')
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/skillsanity_behaviour", "{self._skill_behaviour}")')
                # Craftsanity metadata for the in-game panel tab.
                # Written on every sync so the panel works after reconnects.
                if self._craftsanity_threshold and self._craftsanity_max_value:
                    self.dfhack.run_command("lua",
                        f'dfhack.persistent.saveWorldDataString("dwarfipelago/craftsanity_threshold",'
                        f' "{int(self._craftsanity_threshold)}")')
                    self.dfhack.run_command("lua",
                        f'dfhack.persistent.saveWorldDataString("dwarfipelago/craftsanity_max",'
                        f' "{int(self._craftsanity_max_value)}")')
                    if self._crafting_locations:
                        seen: dict[str, str] = {}
                        for loc_data in self._crafting_locations.values():
                            item     = loc_data["item"]
                            material = loc_data["material"]
                            flag     = (item.replace(" ", "_") + ("_" + material if material else "")).lower()
                            if flag not in seen:
                                seen[flag] = (material + " " if material else "") + item
                        entries = ",".join(f'["{f}"]="{l}"' for f, l in seen.items())
                        self.dfhack.run_command(
                            "lua",
                            f'dfhack.persistent.saveWorldDataString("dwarfipelago/craftsanity_labels",'
                            f' require("json").encode({{{entries}}}))'
                        )
                self._slot_data_synced = True
                await self.getAPKeyValue("Dwarfipelago/"+str(self.seed)+"/completed_locations")
                logger.info(f"Synced slot data → goal={goal}, wealth_goal={wealth_goal}, pop_goal={pop_goal}, dl_threshold={dl_threshold}")
            else:
                logger.error(f'Your APworld and DF mod do not match: APworld verison: {self.version}  Mod version: {script_version}. Please correct this issue before playing.')
        else:
            logger.error(f'This saved world does not match this slot. Please load the correct world or create a new one.')

    async def _apply_received_deathlinks(self):
        """
        Flush any incoming DeathLink bounces queued by on_package into DFHack
        persistent storage, where the Lua poll loop will pick them up and kill
        threshold-many dwarves per link.
        """
        if self._pending_recv_deathlinks <= 0:
            return
        n, self._pending_recv_deathlinks = self._pending_recv_deathlinks, 0
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.dfhack.run_command(
                "lua",
                f"local c = tonumber(dfhack.persistent.getWorldDataString"
                f'("dwarfipelago/pending_recv") or "0") or 0; '
                f'dfhack.persistent.saveWorldDataString("dwarfipelago/pending_recv", tostring(c + {n}))',
            ),
        )
        mode = f"{self._deathlink_threshold}% of population" if self._deathlink_percentage else f"{self._deathlink_threshold} dwarves"
        logger.info(f"Queued {n} received DeathLink(s) - Lua will kill {mode} per link")

    async def _check_deathlink_send(self):
        """
        Compare the Lua-side death counter against how many DeathLinks we've
        already sent. For each new multiple of deathlink_threshold deaths,
        persist the new count then broadcast one DeathLink Bounce to the AP server.
        """
        if not self._deathlink_enabled or self._deathlink_threshold <= 0:
            return

        def read_counts():
            dc = self.dfhack.run_command(
                "lua",
                'print(dfhack.persistent.getWorldDataString("dwarfipelago/death_count") or "0")',
            )
            ds = self.dfhack.run_command(
                "lua",
                'print(dfhack.persistent.getWorldDataString("dwarfipelago/deathlinks_sent") or "0")',
            )
            pop = None
            if self._deathlink_percentage:
                pop = self.dfhack.run_command(
                    "lua",
                    'local c=0; for _,u in ipairs(df.global.world.units.active) do '
                    'if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then c=c+1 end end; print(c)',
                )
            return dc, ds, pop

        dc_raw, ds_raw, pop_raw = await asyncio.get_event_loop().run_in_executor(None, read_counts)
        try:
            death_count  = int((dc_raw or "0").strip())
            already_sent = int((ds_raw or "0").strip())
        except ValueError:
            return

        if self._deathlink_percentage:
            try:
                pop = max(1, int((pop_raw or "0").strip()))
            except ValueError:
                return
            threshold = max(1, int(pop * self._deathlink_threshold / 100))
        else:
            threshold = self._deathlink_threshold

        to_send = death_count // threshold - already_sent
        if to_send <= 0:
            return

        fortress_name = getattr(self, "auth", "The Fortress")
        new_sent = already_sent
        for _ in range(to_send):
            new_sent += 1
            # Persist the incremented count before sending so a crash can't double-send.
            n = new_sent
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.dfhack.run_command(
                    "lua",
                    f'dfhack.persistent.saveWorldDataString("dwarfipelago/deathlinks_sent", "{n}")',
                ),
            )
            await self.send_msgs([{
                "cmd": "Bounce",
                "tags": ["DeathLink"],
                "data": {
                    "time": time.time(),
                    "cause": f"{threshold} dwarves have met their end in {fortress_name}",
                    "source": fortress_name,
                },
            }])

        logger.info(f"Sent {to_send} DeathLink(s) - {death_count} total deaths / threshold {threshold}")

    async def _check_goal_complete(self):
        """
        Poll the goal-complete flag written by the Lua mod and send
        ClientStatus.CLIENT_GOAL to the AP server the first time it's set.
        """
        if self._goal_complete:
            return
        output = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.dfhack.run_command(
                "lua",
                'print(dfhack.persistent.getWorldDataString("dwarfipelago/goal_complete") or "")',
            ),
        )
        if output and output.strip() == "1":
            self._goal_complete = True
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            logger.info("Goal complete - sent ClientStatus.CLIENT_GOAL to AP server")

    async def _check_cave_discoveries(self):
        """
        Poll the Lua-side cave discovery flags and send AP location checks for
        each cave a dwarf has entered. Custom Cave N maps to BASE_ID + 2300 + (N-1).
        """
        if not self._custom_caves_enabled:
            return

        CAVE_BASE_ID = 37372300  # BASE_ID + 2300

        def read_discoveries():
            results = {}
            for idx in range(1, 7):
                if idx in self._discovered_caves:
                    continue
                raw = self.dfhack.run_command(
                    "lua",
                    f'print(dfhack.persistent.getWorldDataString("dwarfipelago/cave/{idx}/discovered") or "0")',
                )
                if raw and raw.strip() == "1":
                    results[idx] = CAVE_BASE_ID + (idx - 1)
            return results

        newly = await asyncio.get_event_loop().run_in_executor(None, read_discoveries)
        for cave_idx, loc_id in newly.items():
            await self.send_msgs([{"cmd": "LocationChecks", "locations": [loc_id]}])
            self._discovered_caves.add(cave_idx)
            logger.info(f"Custom cave {cave_idx} discovered — sent location check {loc_id}")

    def init_crafting_locations(self):
        last_item = ""
        last_material = ""
        for crafts in self._crafting_locations:
            if self._crafting_locations[crafts]["item"] == last_item and self._crafting_locations[crafts]["material"] == last_material:
                continue
            storage_name ="dwarfipelago/craft_count/"
            if self._crafting_locations[crafts]["material"] == "": #material type doesn't matter, add them all
                storage_name += self._crafting_locations[crafts]["item"].replace(" ", "_")
            else:
                storage_name += self._crafting_locations[crafts]["item"].replace(" ", "_") + "_"+self._crafting_locations[crafts]["material"]
            storage_name = storage_name.lower()
            self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("{storage_name}", "0")')
            last_item = self._crafting_locations[crafts]["item"]
            last_material = self._crafting_locations[crafts]["material"]
    
    async def update_energy(self):
        if self.energy_link_enabled and self.last_energy != self.current_energy_link_value:
            self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/energy_link", "{int(self.current_energy_link_value or 0)}")')
            self.last_energy = self.current_energy_link_value

    async def new_energy(self):
        if self.energy_link_enabled:
            used_energy = self.dfhack.run_command("lua", 'print(dfhack.persistent.getWorldDataString("dwarfipelago/use_energy_link") or "N")')
            if used_energy and used_energy.strip() == "Y":
                deposit_raw = self.dfhack.run_command("lua", 'print(dfhack.persistent.getWorldDataString("dwarfipelago/energy_deposit") or "0")')
                try:
                    deposit = int((deposit_raw or "0").strip())
                except ValueError:
                    deposit = 0
                if deposit > 0:
                    await self.send_msgs([{
                        "cmd": "Set", "key": self.energylink_key, "operations":
                            [{"operation": "add", "value": deposit}]
                    }])
                    logger.debug(f"EnergyLink: Sent {format_SI_prefix(deposit)}*")
                self.dfhack.run_command("lua", 'dfhack.persistent.saveWorldDataString("dwarfipelago/energy_deposit", "0")')
                self.dfhack.run_command("lua", 'dfhack.persistent.saveWorldDataString("dwarfipelago/use_energy_link", "N")')

    async def _check_caravan_request(self):
        """Handle caravan call: deduct seasonal energy cost from pool, then approve spawn in Lua."""
        if not self.energy_link_enabled:
            return
        flag = self.dfhack.run_command("lua", 'print(dfhack.persistent.getWorldDataString("dwarfipelago/request_caravan") or "0")')
        if not (flag and flag.strip() == "1"):
            return
        self.dfhack.run_command("lua", 'dfhack.persistent.saveWorldDataString("dwarfipelago/request_caravan", "0")')
        cost_raw = self.dfhack.run_command("lua", 'print(dfhack.persistent.getWorldDataString("dwarfipelago/caravan_energy_cost") or "0")')
        try:
            cost = int((cost_raw or "0").strip())
        except ValueError:
            cost = 0
        if cost <= 0:
            return
        pool = self.current_energy_link_value
        if pool is None or pool < cost:
            logger.debug(f"EnergyLink: Caravan denied - need {format_SI_prefix(cost)}*, have {format_SI_prefix(pool or 0)}*")
            return
        self.last_deplete = time.time()
        await self.send_msgs([{
            "cmd": "Set", "key": self.energylink_key,
            "operations": [{"operation": "add", "value": -cost},
                           {"operation": "max", "value": 0}],
            "last_deplete": self.last_deplete
        }])
        self.dfhack.run_command("lua", 'dfhack.persistent.saveWorldDataString("dwarfipelago/spawn_caravan_approved", "1")')
        logger.debug(f"EnergyLink: Caravan approved, deducted {format_SI_prefix(cost)}*")

    async def _sync_shop(self):
        """
        Scout the shop-slot locations and write each slot's contents to DFHack
        storage for the in-game Shop tab: the item name, the player who receives
        it, the slot's coin price + coffer tier, and whether it's been bought.
        Sends LocationScouts once per AP session; re-writes only when something
        (e.g. a bought flag) changes.
        """
        shop = self.slot_data.get("shop", {})
        if not shop:
            if not getattr(self, "_shop_warned_empty", False):
                self._shop_warned_empty = True
                logger.info("Shop: slot_data has no 'shop' entry - this apworld/seed has no shop "
                            "(or an older apworld was used to generate).")
            return
        shop_ids = [int(k) for k in shop.keys()]
        if not self._shop_scout_sent:
            logger.info(f"Shop: scouting {len(shop_ids)} shop slots")
            await self.send_msgs([{
                "cmd": "LocationScouts", "locations": shop_ids, "create_as_hint": 0,
            }])
            self._shop_scout_sent = True

        entries: dict[str, Any] = {}
        for sid in shop_ids:
            info = self.locations_info.get(sid)
            if not info:
                continue  # scout reply not in yet for this slot
            meta = shop[str(sid)]
            try:
                item_name = self.item_names.lookup_in_slot(info.item, info.player)
            except Exception:
                item_name = str(info.item)
            player_name = self.player_names.get(info.player, str(info.player))
            entries[str(meta["slot"])] = {
                "id": sid,
                "slot": meta["slot"],
                "tier": meta["tier"],
                "price": meta["price"],
                "item": item_name,
                "player": player_name,
                "flags": int(getattr(info, "flags", 0) or 0),
                "bought": 1 if sid in self.checked_locations else 0,
            }
        if not entries:
            return

        # ensure_ascii keeps cross-game item names safe inside the Lua string;
        # escape backslashes then quotes so the JSON survives the Lua literal.
        payload = json.dumps(entries, ensure_ascii=True, sort_keys=True)
        if payload == self._shop_last_sig:
            return
        self._shop_last_sig = payload
        escaped = payload.replace("\\", "\\\\").replace('"', '\\"')
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.dfhack.run_command(
                "lua",
                f'dfhack.persistent.saveWorldDataString("dwarfipelago/shop", "{escaped}")',
            ),
        )
        logger.info(f"Shop: wrote {len(entries)} slot(s) to DFHack storage")

    async def _check_shop_purchase(self):
        """
        Buy bridge (mirrors _check_caravan_request): the Lua 'buy-shop' command
        charges the minted coins and appends the slot number to the JSON queue at
        dwarfipelago/shop_buy. We drain the queue and send those slots' location
        checks, releasing each item to its recipient. (A queue, not a single
        value, so two quick purchases can't clobber each other.)
        """
        shop = self.slot_data.get("shop", {})
        if not shop:
            return
        raw = self.dfhack.run_command(
            "lua", 'print(dfhack.persistent.getWorldDataString("dwarfipelago/shop_buy") or "")')
        raw = (raw or "").strip()
        if not raw or raw in ("[]", "nil", "0"):
            return
        try:
            slots = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return
        if not isinstance(slots, list) or not slots:
            return
        self.dfhack.run_command(
            "lua", 'dfhack.persistent.saveWorldDataString("dwarfipelago/shop_buy", "[]")')
        loc_ids = []
        for slot in slots:
            loc_id = next((int(k) for k, m in shop.items() if m["slot"] == slot), None)
            if loc_id is not None and loc_id not in self.checked_locations:
                loc_ids.append(loc_id)
        if loc_ids:
            await self.send_msgs([{"cmd": "LocationChecks", "locations": loc_ids}])
            logger.info(f"Shop: purchased slots {slots} -> locations {loc_ids}")


    async def _crafting_location_checks(self):
        """Read new crafting location checks from persistent storage and report them to AP."""
        local_checks = []
        # Wait until the AP Get reply has populated the completed list. Using an
        # explicit flag (not len()==0) so a legitimately-empty list doesn't block
        # checks forever.
        if not self._completed_locations_loaded:
            return
        if not self._crafting_locations:
            return

        # Build the set of unique storage keys we need to read, skipping
        # already-completed locations.
        key_to_pair: dict[str, tuple[str, str]] = {}
        for crafts in self._crafting_locations:
            if crafts in self._completed_crafting_locations:
                continue
            item     = self._crafting_locations[crafts]["item"]
            material = self._crafting_locations[crafts]["material"]
            pair     = (item, material)
            if pair in key_to_pair.values():
                continue
            if material == "":
                storage_name = "dwarfipelago/craft_count/" + item.replace(" ", "_").lower()
            else:
                storage_name = "dwarfipelago/craft_count/" + (item.replace(" ", "_") + "_" + material).lower()
            key_to_pair[storage_name] = pair

        if not key_to_pair:
            return

        # Single batched RPC: read all keys in one Lua call and return JSON.
        keys_lua = "{" + ",".join(f'"{k}"' for k in key_to_pair) + "}"
        lua_code = (
            f"local r={{}};for _,k in ipairs({keys_lua}) do "
            f"r[k]=dfhack.persistent.getWorldDataString(k) or '0' end;"
            f"print(require('json').encode(r))"
        )
        raw = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.dfhack.run_command("lua", lua_code)
        )
        if not raw or not raw.strip():
            return
        try:
            counts = json.loads(raw.strip())
        except json.JSONDecodeError:
            logger.warning(f"_crafting_location_checks: failed to parse batch result: {raw!r}")
            return

        # Build (item, material) → count lookup.
        count_lookup: dict[tuple[str, str], int] = {}
        for storage_key, pair in key_to_pair.items():
            val = counts.get(storage_key, "0")
            try:
                count_lookup[pair] = int(val) if val and val not in ("nil", "") else 0
            except (ValueError, AttributeError):
                count_lookup[pair] = 0

        # Diagnostic (debug mode only): surface nonzero craft counts so a
        # key/flag mismatch is easy to spot. Toggle with /dfdebug.
        if self.debug_mode:
            nonzero = {k: v for k, v in count_lookup.items() if v > 0}
            if nonzero:
                self.debug(f"Craft counts: {nonzero}  (threshold={self._craftsanity_threshold}, max={self._craftsanity_max_value})")

        threshold = self._craftsanity_threshold or 1  # guard against divide-by-zero

        # Evaluate each location against the counts.
        for crafts in self._crafting_locations:
            if crafts in self._completed_crafting_locations:
                continue
            item     = self._crafting_locations[crafts]["item"]
            material = self._crafting_locations[crafts]["material"]
            amount_crafted = count_lookup.get((item, material), 0)
            if amount_crafted == 0:
                continue
            # Each location carries a tier number (1, 2, …, max_id); the check
            # fires when amount_crafted / threshold >= that tier number.
            # We no longer short-circuit on amount_crafted >= max_value because
            # that path fires every remaining tier at once when a work-order batch
            # overshoots the max, and can fire the final check early when
            # max_value is not divisible by threshold.  The tier formula below
            # covers all cases including the final check.
            if amount_crafted / threshold >= self._crafting_locations[crafts]["threshold"]:
                local_checks.append(int(crafts))

        if local_checks:
            await self.send_msgs([{"cmd": "LocationChecks", "locations": local_checks}])
        for location in local_checks:
            location_str = str(location)
            self._completed_crafting_locations.append(location_str)
            await self.setAPKeyValue(
                "Dwarfipelago/" + str(self.seed) + "/completed_locations",
                self._completed_crafting_locations,
            )
            location_name = self._crafting_locations[location_str]["location_name"]
            self.dfhack.run_command(
                "lua", f'dfhack.gui.showAnnouncement("{location_name} Completed!", COLOR_GREEN)'
            )
    
    async def _skill_location_checks(self):
        """Read tracked skill levels from persistent storage and fire any skill
        locations whose level threshold has been reached. Mirrors
        _crafting_location_checks; completed ids share the same AP storage list."""
        if not self._completed_locations_loaded:
            return
        if not self._skill_locations:
            return

        # Unique storage keys to read (one per skill flag), skipping skills whose
        # locations are all already completed is not worth the bookkeeping - there
        # are at most ~60 flags, so just read them all in one batch.
        flag_keys: dict[str, str] = {}
        for skill in self._skill_locations:
            flag = self._skill_locations[skill]["skill"].lower()
            flag_keys["dwarfipelago/skill/" + flag] = flag
        if not flag_keys:
            return

        keys_lua = "{" + ",".join(f'"{k}"' for k in flag_keys) + "}"
        lua_code = (
            f"local r={{}};for _,k in ipairs({keys_lua}) do "
            f"r[k]=dfhack.persistent.getWorldDataString(k) or '0' end;"
            f"print(require('json').encode(r))"
        )
        raw = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.dfhack.run_command("lua", lua_code)
        )
        if not raw or not raw.strip():
            return
        try:
            levels_raw = json.loads(raw.strip())
        except json.JSONDecodeError:
            logger.warning(f"_skill_location_checks: failed to parse batch result: {raw!r}")
            return

        level_by_flag: dict[str, int] = {}
        for storage_key, flag in flag_keys.items():
            val = levels_raw.get(storage_key, "0")
            try:
                level_by_flag[flag] = int(val) if val and val not in ("nil", "") else 0
            except (ValueError, AttributeError):
                level_by_flag[flag] = 0

        if self.debug_mode:
            nonzero = {f: v for f, v in level_by_flag.items() if v > 0}
            if nonzero:
                self.debug(f"Skill levels: {nonzero}")

        local_checks = []
        for skill in self._skill_locations:
            if skill in self._completed_crafting_locations:
                continue
            flag = self._skill_locations[skill]["skill"].lower()
            if level_by_flag.get(flag, 0) >= self._skill_locations[skill]["threshold"]:
                local_checks.append(int(skill))

        if local_checks:
            await self.send_msgs([{"cmd": "LocationChecks", "locations": local_checks}])
        for location in local_checks:
            location_str = str(location)
            self._completed_crafting_locations.append(location_str)
            await self.setAPKeyValue(
                "Dwarfipelago/" + str(self.seed) + "/completed_locations",
                self._completed_crafting_locations,
            )
            location_name = self._skill_locations[location_str]["location_name"]
            self.dfhack.run_command(
                "lua", f'dfhack.gui.showAnnouncement("{location_name} Completed!", COLOR_GREEN)'
            )

    def init_skill_locations(self):
        # Initialise one storage key per enabled skill (deduped - each skill has 15
        # level locations sharing a flag). Writing "0" marks the skill as tracked;
        # the Lua scanner only updates keys that already exist, so untracked skills
        # stay out of both the checks and the panel. Runs once per world (fresh
        # seed), so it never wipes accumulated levels on reconnect.
        if not self._skill_locations:
            return
        seen = set()
        for skill in self._skill_locations:
            flag = self._skill_locations[skill]["skill"].lower()
            if flag in seen:
                continue
            seen.add(flag)
            storage_name = "dwarfipelago/skill/" + flag
            self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("{storage_name}", "0")')

    async def setAPKeyValue(self, key:str, value:list[int]):
        await self.send_msgs([{
            "cmd": "Set",
            "key": key,
            "default": hex(0),
            "want_reply": False,
            "operations": [{"operation": "replace",
            "value": value}]
        }])

    async def getAPKeyValue(self, key:str) -> str:
        await self.send_msgs([{
            "cmd": "Get",
            "keys": [key],
        }])
    # ── CommonClient overrides ────────────────────────────────────────────────

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()
       

    def on_package(self, cmd: str, args: dict):
        super().on_package(cmd, args)
        if cmd == "Bounced" and "DeathLink" in args.get("tags", []):
            source = args.get("data", {}).get("source", "")
            # Ignore bounces that originated from us.
            if source != getattr(self, "auth", None):
                cause = args.get("data", {}).get("cause", "unknown cause")
                logger.info(f"DeathLink received from {source!r}: {cause}")
                self._pending_recv_deathlinks += 1
        if cmd == "Connected":
            # Start DFHack polling and (when inside AP) the server connection as
            # concurrent asyncio tasks so neither blocks the other.
            self.slot_data: dict[str, Any] = args.get("slot_data", {})
            self._shop_scout_sent = False  # re-scout shop slots for this AP session
            self._shop_last_sig = None
            # Register as a DeathLink participant when the option is on. This adds
            # the "DeathLink" tag and sends a ConnectUpdate, which is what tells the
            # server to route DeathLink bounces to/from this slot. Without it the
            # server never treats us as a participant, so nothing is exchanged.
            self._deathlink_enabled = bool(self.slot_data.get("deathlink", 0))
            if self._deathlink_enabled:
                asyncio.create_task(self.update_death_link(True))
            self._custom_caves_enabled = bool(self.slot_data.get("custom_caves", 0))
            self.energy_link_enabled = bool(self.slot_data.get("energy_link", 0))
            if self.energy_link_enabled:
                async_start(self.send_msgs([{
                    "cmd": "SetNotify", "keys": [self.energylink_key]
                }]))
            self.dfhack_task = asyncio.create_task(self.dfhack_poll_loop(), name="DFHack poll")
        elif cmd == "Retrieved":
            key = "Dwarfipelago/"+str(self.seed)+"/completed_locations"
            if key in args['keys']:
                stored = args['keys'][key]
                if stored is not None:
                    self._completed_crafting_locations = stored
                else:
                    self._completed_crafting_locations = [0]
                # Mark loaded so _crafting_location_checks can run even when the
                # completed list is legitimately empty/[0].
                self._completed_locations_loaded = True
                self.debug(f"Loaded {len(self._completed_crafting_locations)} completed craft location(s) from AP storage")
            #response from the Get Command
        elif cmd == "SetReply":
            if args["key"].startswith("EnergyLink"):
                if self.energy_link_enabled and args.get("last_deplete", -1) == self.last_deplete:
                    # it's our deplete request
                    gained = int(args["original_value"] - args["value"])
                    gained_text = format_SI_prefix(gained) + "*"
                    if gained:
                        logger.debug(f"EnergyLink: Received {gained_text}. "
                                     f"{format_SI_prefix(args['value'])}* remaining.")

    def on_print_json(self, args: dict[Any, Any]):
        if self.ui:
            self.ui.print_json(copy.deepcopy(args["data"]))
            self.send_notification_to_dwarffortress(args)
        else:
            text = self.jsontotextparser(copy.deepcopy(args["data"]))
            logger.info(text)
            self.send_notification_to_dwarffortress(args)

    def send_notification_to_dwarffortress(self, args: dict[Any, Any]):
            datatype = args.get("type")
            if datatype == "ItemSend":
                item = args["item"]
                if not self.slot_concerns_self(args["receiving"]): # You found someone else's item
                    if self.slot_concerns_self(item.player):
                        to_player = self.player_names[args["receiving"]]
                        item_name = self.item_names.lookup_in_slot(int(args["data"][2]["text"]), args["receiving"])
                        #COLOR_BROWN is actually Yellow in this DFHack version
                        self.dfhack.run_command("lua", f'dfhack.gui.showAnnouncement("You found {to_player} their {item_name}.", COLOR_BROWN)')
                elif self.slot_concerns_self(args["receiving"]): # This is your item
                    player = self.player_names[int(args["data"][0]["text"])]
                    to_player = self.player_names[args["receiving"]]
                    item_name = self.item_names.lookup_in_slot(int(args["data"][2]["text"]))
                    if player == to_player: # you found your own item
                        self.dfhack.run_command("lua", f'dfhack.gui.showAnnouncement("You found your {item_name}.", COLOR_GREEN)')
                    else:
                        self.dfhack.run_command("lua", f'dfhack.gui.showAnnouncement("{player} found your {item_name}.", COLOR_GREEN)')
            elif datatype == "ItemCheat":
                if self.slot_concerns_self(args["receiving"]): # its your item
                    item = args["item"]
                    item_name = self.item_names.lookup_in_slot(item.item)
                    self.dfhack.run_command("lua", f'dfhack.gui.showAnnouncement("You received your {item_name}.", COLOR_GREEN)')
            elif datatype == "Goal": 
                if self.slot_concerns_self(args["slot"]):
                    self.dfhack.run_command("lua", f'dfhack.gui.showPopupAnnouncement("Congratulations! You achieved your goal!", COLOR_BLUE)')


    async def disconnect(self, allow_autoreconnect: bool = False):
        self.dfhack.disconnect()
        await super().disconnect(allow_autoreconnect)

    @property
    def energy_link_status(self) -> str:
        if not self.energy_link_enabled:
            return "Disabled"
        elif self.current_energy_link_value is None:
            return "Standby"
        else:
            return f"{format_SI_prefix(self.current_energy_link_value)}*"
        
    @property
    def energylink_key(self) -> str:
        if self.generator_version >= (0, 4, 2):
            return f"EnergyLink{self.team}"
        else:
            return "EnergyLink"


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    try:
        import colorama
        colorama.init()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Dwarfipelago - Dwarf Fortress AP client")
    parser.add_argument("--connect",      default="archipelago.gg:38281", help="AP server address (host:port)")
    parser.add_argument("--name",        default=None,                   help="Slot name")
    parser.add_argument("--password",    default=None,                   help="Room password")
    parser.add_argument("--dfhack-host", default=DFHACK_HOST,            help="DFHack host")
    parser.add_argument("--dfhack-port", default=DFHACK_PORT, type=int,  help="DFHack port")
    # parse_known_args tolerates extra flags that the AP launcher may inject
    # (e.g. multiprocessing internal arguments) without exiting with an error.
    args, _unknown = parser.parse_known_args()

    async def run():
        if "Dwarfipelago Client" in args:
            args.remove("Dwarfipelago Client")

        ctx = DwarfFortressContext(args.connect, args.password)
        ctx.dfhack.host = args.dfhack_host
        ctx.dfhack.port = args.dfhack_port


        if args.name:
            ctx.auth = args.name

        exe = _get_df_executable()
        if not exe:
            subprocess.Popen([exe], cwd=cwd)
            return

        cwd = os.path.dirname(exe)
        try:
            subprocess.Popen([exe], cwd=cwd)
        except OSError as e:
            logger.error("Failed to launch Dwarf Fortress", str(e))

        # Start DFHack polling and (when inside AP) the server connection as
        # concurrent asyncio tasks so neither blocks the other.
        # ctx.dfhack_task = asyncio.create_task(ctx.dfhack_poll_loop(), name="DFHack poll")
        # ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        # Show the AP client GUI window (kivy-based console).
        # run_gui() schedules the UI as an asyncio task and returns immediately.
        ctx.run_gui()
        # Block until the user closes the window or the client disconnects.
        await ctx.exit_event.wait()
        ctx.dfhack_task.cancel()
        await ctx.shutdown()

    asyncio.run(run())


if __name__ == "__main__":
    main()
