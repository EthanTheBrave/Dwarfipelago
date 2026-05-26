"""
DwarfFortressClient — bridges a running Dwarf Fortress (via DFHack's remote API)
and an Archipelago multiworld server (via WebSocket).

Run with:
    python DwarfFortressClient.py --server archipelago.gg:PORT --name YourSlotName

DFHack remote API listens on 127.0.0.1:5000 by default.
"""

import asyncio
import json
import logging
import os
import socket
import struct
import argparse
import subprocess
import sys
import time
from typing import Any, Optional
from CommonClient import CommonContext, server_loop, ClientCommandProcessor, logger
from NetUtils import ClientStatus

_STEAM_CANDIDATES: list[str] = [
    # Windows — 32-bit Steam
    r"C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress\Dwarf Fortress.exe",
    # Windows — 64-bit Steam
    r"C:\Program Files\Steam\steamapps\common\Dwarf Fortress\Dwarf Fortress.exe",
    # Linux — default Steam library
    os.path.expanduser("~/.steam/steam/steamapps/common/Dwarf Fortress/dfhack"),
    # Linux — flatpak Steam
    os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam"
                       "/steamapps/common/Dwarf Fortress/dfhack"),
    # macOS — Steam
    os.path.expanduser("~/Library/Application Support/Steam"
                       "/steamapps/common/Dwarf Fortress/dfhack"),
]

# ── DFHack Remote API ─────────────────────────────────────────────────────────

DFHACK_HOST = "127.0.0.1"
DFHACK_PORT = 5000

# DFHack remote API handshake — magic (8 bytes) + version int32 LE (4 bytes) = 12 bytes total.
# The client sends the request magic+version; the server replies with reply magic+version.
# If only the 8-byte magic is sent, DFHack waits for the remaining 4 bytes and the
# connection hangs until our recv() times out — hence "DFHack not reachable: timed out".
_DFHACK_VERSION       = struct.pack("<i", 1)
DFHACK_MAGIC_REQUEST  = b"DFHack?\n" + _DFHACK_VERSION   # 12 bytes
DFHACK_MAGIC_REPLY    = b"DFHack!\n" + _DFHACK_VERSION   # 12 bytes

# DFHack RPC reply / special IDs (carried in the message header's id field).
# Source: DFHack RemoteClient.h — enum DFHackReplyCode : int16_t
# See https://docs.dfhack.org/en/stable/docs/dev/Remote.html
RPC_METHOD_BIND  =  0   # BindMethod request — always method id 0
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
            # Handshake done — widen the timeout for normal RPC calls.
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
        if self._sock:
            self._sock.close()
            self._sock = None
        # Clear the cached method ID so BindMethod is re-issued on the next connection.
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
        # from DFHack's stack — extract fields by offset rather than treating the
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

        CoreBindRequest.input_msg and output_msg are proto2 *required* fields —
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
        logger.error(f"BindMethod failed for {method!r}: reply_id={reply_id}, data={data!r}")
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
        try:
            if not hasattr(self, "_run_cmd_id"):
                # CoreBindRequest.input_msg and output_msg are proto2 *required*
                # fields — must pass the fully-qualified proto type names.
                self._run_cmd_id = self._bind_method(
                    "RunCommand",
                    "dfproto.CoreRunCommandRequest",
                    "dfproto.EmptyMessage",
                )
                if self._run_cmd_id < 0:
                    logger.error("Failed to bind RunCommand")
                    return None

            # Encode CoreRunCommandRequest { command(1), arguments(2 repeated) }
            body = _pb_string(1, command)
            for arg in args:
                body += _pb_string(2, arg)
            self._send_rpc(self._run_cmd_id, body)

            # Drain TextNotification packets until we receive a Result or Error.
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
                    logger.warning(f"DFHack RunCommand failed (id={reply_id}): {data!r}")
                    return None

            return "".join(output_parts)

        except Exception as e:
            logger.warning(f"DFHack run_command error: {e}")
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
            logger.warning(f"Failed to parse pending checks — {e!r} — raw: {output!r}")
            return []

    def deliver_item(self, item_name: str):
        """Deliver a received AP item to the fortress by calling the Lua item handler."""
        safe_name = item_name.replace("\\", "\\\\").replace('"', '\\"')
        result = self.run_command(
            "lua",
            f'reqscript("internal/dwarfipelago/items").receive("{safe_name}")',
        )
        if result is None:
            logger.warning(f"deliver_item: RPC returned None for {item_name!r} — connection lost?")
        else:
            logger.info(f"Delivered item to fortress: {item_name!r} (lua output: {result.strip()!r})")


# ── Archipelago Client ────────────────────────────────────────────────────────

class DwarfFortressContext(CommonContext):
    """
    Archipelago client context for Dwarf Fortress.

    Connects to both:
    - The DFHack remote API (TCP 5000) to read fortress state
    - The Archipelago server (WebSocket) to send/receive multiworld messages
    """

    game = "Dwarf Fortress"
    items_handling = 0b111  # receive all items (local + remote + starting inventory)

    def __init__(self, server_address: str, password: Optional[str] = None):
        super().__init__(server_address, password)
        self.dfhack = DFHackConnection()
        self._poll_interval = 5.0        # seconds between fortress state polls
        self._received_index = 0         # last applied item index
        self._slot_data_synced = False   # Loaded the correct saved world
        self._goal_complete = False
        self._deathlink_threshold = 5    # dwarves per DeathLink (overridden by slot data)
        self._pending_recv_deathlinks = 0  # incoming DeathLink bounces waiting to be applied
        self._mod_started = False        # True once dwarfipelago/main start has succeeded
        self._world_loaded = False       # True while DF has an active world loaded

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
                # ── World-loaded guard ────────────────────────────────────────
                # saveWorldDataString / getWorldDataString crash when no world is
                # loaded. Skip every storage-touching operation until DF is in a
                # loaded fortress or adventure-mode session.
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.dfhack.run_command(
                        "lua", "print(dfhack.isWorldLoaded() and '1' or '0')"
                    ),
                )
                world_loaded = bool(result and result.strip() == "1")

                if not world_loaded:
                    if self._world_loaded:
                        # Transition: player returned to the main menu.
                        self._world_loaded = False
                        self._mod_started = False
                        self._slot_data_synced = False
                        logger.info("World unloaded — pausing fortress polling until a save is loaded")
                    await asyncio.sleep(self._poll_interval)
                    continue

                if not self._world_loaded:
                    self._world_loaded = True
                    logger.info("World loaded — resuming fortress polling")

                # ── Auto-start mod ────────────────────────────────────────────
                # 'dwarfipelago start' is safe to call on an already-running mod;
                # it just re-registers hooks. We do it once per world load.
                if not self._mod_started:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.dfhack.run_command("dwarfipelago", "start"),
                    )
                    self._mod_started = True
                    logger.info("Auto-started dwarfipelago Lua mod")

                # ── Fortress operations (world guaranteed loaded) ─────────────
                self._sync_slot_data()
                if self._slot_data_synced:
                    await self._apply_received_deathlinks()
                    await self._process_new_checks()
                    await self._apply_pending_items()
                    await self._check_deathlink_send()
                    await self._check_goal_complete()

            except Exception as e:
                logger.warning(f"DFHack poll error: {e}")
                self.dfhack.disconnect()
                self._slot_data_synced = False
                self._mod_started = False
                self._world_loaded = False

            await asyncio.sleep(self._poll_interval)

    async def _process_new_checks(self):
        """Read new location checks from the Lua mod and report them to AP."""
        location_ids = await asyncio.get_event_loop().run_in_executor(
            None, self.dfhack.pop_pending_checks
        )
        if location_ids:
            logger.info(f"New checks: {location_ids}")
            await self.send_msgs([{
                "cmd": "LocationChecks",
                "locations": location_ids,
            }])

    async def _apply_pending_items(self):
        """Apply any received AP items that haven't been delivered yet."""
        # self.items_received is populated by CommonClient when the server sends ReceivedItems.
        # We apply items in order starting from self._received_index.
        pending = len(self.items_received) - self._received_index
        if pending > 0:
            logger.info(f"Applying {pending} pending item(s) starting at index {self._received_index}")

        for i in range(self._received_index, len(self.items_received)):
            network_item = self.items_received[i]

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

            logger.info(f"Delivering item [{i}]: id={network_item.item} → name={item_name!r}")
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

    def _sync_slot_data(self):
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
        dl_threshold = slot_data.get("deathlink_threshold", 5)
        seed         = slot_data.get("seed", 0)
        current_seed = self.dfhack.run_command("lua", f'print(dfhack.persistent.getWorldDataString("dwarfipelago/seed"))')
        self._deathlink_threshold = int(dl_threshold)
        if current_seed == 'nil' or current_seed == str(seed):
            def write():
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/goal", "{goal}")')
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/wealth_goal", "{wealth_goal}")')
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/pop_goal", "{pop_goal}")')
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/deathlink_threshold", "{dl_threshold}")')
                self.dfhack.run_command("lua", f'dfhack.persistent.saveWorldDataString("dwarfipelago/seed", "{seed}")')
            write()
            self._slot_data_synced = True
            logger.info(f"Synced slot data → goal={goal}, wealth_goal={wealth_goal}, pop_goal={pop_goal}, dl_threshold={dl_threshold}")
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
        logger.info(f"Queued {n} received DeathLink(s) — Lua will kill {n * self._deathlink_threshold} dwarves")

    async def _check_deathlink_send(self):
        """
        Compare the Lua-side death counter against how many DeathLinks we've
        already sent. For each new multiple of deathlink_threshold deaths,
        persist the new count then broadcast one DeathLink Bounce to the AP server.
        """
        threshold = self._deathlink_threshold
        if threshold <= 0:
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
            return dc, ds

        dc_raw, ds_raw = await asyncio.get_event_loop().run_in_executor(None, read_counts)
        try:
            death_count  = int((dc_raw or "0").strip())
            already_sent = int((ds_raw or "0").strip())
        except ValueError:
            return

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

        logger.info(f"Sent {to_send} DeathLink(s) — {death_count} total deaths / threshold {threshold}")

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
            logger.info("Goal complete — sent ClientStatus.CLIENT_GOAL to AP server")

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
            self.dfhack_task = asyncio.create_task(self.dfhack_poll_loop(), name="DFHack poll")
            self.server_task = asyncio.create_task(server_loop(self), name="server loop")

    async def disconnect(self, allow_autoreconnect: bool = False):
        self.dfhack.disconnect()
        await super().disconnect(allow_autoreconnect)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    try:
        import colorama
        colorama.init()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Dwarfipelago — Dwarf Fortress AP client")
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
