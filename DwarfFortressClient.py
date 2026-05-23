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
import socket
import struct
import argparse
from typing import Optional

# Archipelago CommonClient provides the base WebSocket client and message handling.
# When running standalone (outside the AP installation), we provide a lightweight stub.
try:
    from CommonClient import CommonContext, server_loop, ClientCommandProcessor, logger
    from NetUtils import ClientStatus
    HAS_COMMON_CLIENT = True
except ImportError:
    HAS_COMMON_CLIENT = False
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DwarfFortressClient")

# ── DFHack Remote API ─────────────────────────────────────────────────────────

DFHACK_HOST = "127.0.0.1"
DFHACK_PORT = 5000

DFHACK_MAGIC_REQUEST = b"DFHack?\n"
DFHACK_MAGIC_REPLY   = b"DFHack!\n"

# DFHack RPC reply / special IDs (carried in the message header's id field).
# See https://docs.dfhack.org/en/stable/docs/dev/Remote.html
RPC_METHOD_BIND  =  0   # BindMethod — always id 0
RPC_REPLY_RESULT = -1   # successful result
RPC_REPLY_ERROR  = -2   # error result (protobuf CoreErrorInfo body)
RPC_REPLY_FAIL   = -3   # call failed (non-protobuf)
RPC_REPLY_TEXT   = -5   # TextNotification (console output mid-call)
RPC_HEADER_SIZE  =  8   # two little-endian int32s: id + body_size

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

    Proto structure:
      CoreTextNotification { fragments(1): CoreTextFragment {
          fragments(1): Tile { str(1): string, fg(2), bg(3) } } }
    """
    parts = []
    for frag_bytes in _pb_decode(body).get(1, []):          # CoreTextFragment
        for tile_bytes in _pb_decode(frag_bytes).get(1, []):  # Tile
            for s in _pb_decode(tile_bytes).get(1, []):        # str field
                if isinstance(s, bytes):
                    parts.append(s.decode("utf-8", errors="replace"))
    return "".join(parts)


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
            reply = sock.recv(8)
            if reply != DFHACK_MAGIC_REPLY:
                logger.error(f"DFHack handshake failed: {reply!r}")
                sock.close()
                return False
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
        self._sock.sendall(struct.pack("<ii", method_id, len(body)) + body)

    def _recv_rpc(self) -> tuple[int, bytes]:
        method_id, size = struct.unpack("<ii", self._recv_exactly(RPC_HEADER_SIZE))
        body = self._recv_exactly(size) if size > 0 else b""
        return method_id, body

    def _bind_method(self, method: str, input_msg: str = "", output_msg: str = "") -> int:
        """
        Call BindMethod (always RPC id 0) to obtain the assigned integer ID
        for a named method. Returns -1 on failure.

        Sends:   CoreBindRequest  { method(1), input_msg(2), output_msg(3) }
        Expects: CoreBindReply    { assigned_id(1) }
        """
        body = _pb_string(1, method) + _pb_string(2, input_msg) + _pb_string(3, output_msg)
        self._send_rpc(RPC_METHOD_BIND, body)
        reply_id, data = self._recv_rpc()
        if reply_id == RPC_REPLY_RESULT:
            ids = _pb_decode(data).get(1, [-1])
            return ids[0] if ids else -1
        logger.error(f"BindMethod failed for {method!r}: reply_id={reply_id}")
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
                self._run_cmd_id = self._bind_method(
                    "Core.RunCommand",
                    "CoreRunCommandRequest",
                    "EmptyMessage",
                )
                if self._run_cmd_id < 0:
                    logger.error("Failed to bind Core.RunCommand")
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
                    output_parts.append(_extract_text_notification(data))
                elif reply_id == RPC_REPLY_RESULT:
                    break
                elif reply_id in (RPC_REPLY_ERROR, RPC_REPLY_FAIL):
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
        The mod stores the queue as a JSON array in site data under
        "dwarfipelago/pending_checks". Returns a list of AP location IDs.
        """
        lua = (
            "(function()"
            " local q = dfhack.persistent.getSiteData"
            '("dwarfipelago/pending_checks") or "[]";'
            ' dfhack.persistent.setSiteData("dwarfipelago/pending_checks", "[]");'
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
        self.run_command("lua", f'require("dwarfipelago.items").receive("{safe_name}")')
        logger.info(f"Delivered item to fortress: {item_name}")


# ── Archipelago Client ────────────────────────────────────────────────────────

class DwarfFortressContext(CommonContext if HAS_COMMON_CLIENT else object):
    """
    Archipelago client context for Dwarf Fortress.

    Connects to both:
    - The DFHack remote API (TCP 5000) to read fortress state
    - The Archipelago server (WebSocket) to send/receive multiworld messages
    """

    game = "Dwarf Fortress"
    items_handling = 0b111  # receive all items (local + remote + starting inventory)

    def __init__(self, server_address: str, password: Optional[str] = None):
        if HAS_COMMON_CLIENT:
            super().__init__(server_address, password)
        self.dfhack = DFHackConnection()
        self._poll_interval = 5.0   # seconds between fortress state polls
        self._received_index = 0    # last applied item index
        self._slot_data_synced = False
        self._goal_complete = False

    # ── DFHack polling ────────────────────────────────────────────────────────

    async def dfhack_poll_loop(self):
        """
        Main loop: connect to DFHack, poll for new checks, apply received items.
        Reconnects automatically if DFHack drops.
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
                self._sync_slot_data()
                await self._process_new_checks()
                await self._apply_pending_items()
                await self._check_goal_complete()
            except Exception as e:
                logger.warning(f"DFHack poll error: {e}")
                self.dfhack.disconnect()
                self._slot_data_synced = False  # re-sync on next connection

            await asyncio.sleep(self._poll_interval)

    async def _process_new_checks(self):
        """Read new location checks from the Lua mod and report them to AP."""
        location_ids = await asyncio.get_event_loop().run_in_executor(
            None, self.dfhack.pop_pending_checks
        )
        if location_ids:
            logger.info(f"New checks: {location_ids}")
            if HAS_COMMON_CLIENT:
                await self.send_msgs([{
                    "cmd": "LocationChecks",
                    "locations": location_ids,
                }])

    async def _apply_pending_items(self):
        """Apply any received AP items that haven't been delivered yet."""
        if not HAS_COMMON_CLIENT:
            return
        # self.items_received is populated by CommonClient when the server sends ReceivedItems.
        # We apply items in order starting from self._received_index.
        for i in range(self._received_index, len(self.items_received)):
            network_item = self.items_received[i]
            item_name = (
                self.item_names.lookup_in_game(network_item.item)
                if hasattr(self, "item_names")
                else str(network_item.item)
            )
            await asyncio.get_event_loop().run_in_executor(
                None, self.dfhack.deliver_item, item_name
            )
            self._received_index = i + 1
            # Persist the index so we don't re-deliver on restart.
            self.dfhack.run_command(
                "lua",
                f'dfhack.persistent.setSiteData("dwarfipelago/received_index",'
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
        goal            = slot_data.get("goal", 0)
        wealth_goal     = slot_data.get("wealth_goal_amount", 100000)
        pop_goal        = slot_data.get("population_goal_amount", 300) if HAS_COMMON_CLIENT else 300
        def write():
            self.dfhack.run_command("lua", f'dfhack.persistent.setSiteData("dwarfipelago/goal", "{goal}")')
            self.dfhack.run_command("lua", f'dfhack.persistent.setSiteData("dwarfipelago/wealth_goal", "{wealth_goal}")')
            self.dfhack.run_command("lua", f'dfhack.persistent.setSiteData("dwarfipelago/pop_goal", "{pop_goal}")')
        write()
        self._slot_data_synced = True
        logger.info(f"Synced slot data → goal={goal}, wealth_goal={wealth_goal}, pop_goal={pop_goal}")

    async def _check_goal_complete(self):
        """
        Poll the goal-complete flag written by the Lua mod and send
        ClientStatus.CLIENT_GOAL to the AP server the first time it's set.
        """
        if not HAS_COMMON_CLIENT or self._goal_complete:
            return
        output = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.dfhack.run_command(
                "lua",
                'print(dfhack.persistent.getSiteData("dwarfipelago/goal_complete") or "")',
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
        if HAS_COMMON_CLIENT:
            super().on_package(cmd, args)

    async def disconnect(self, allow_autoreconnect: bool = False):
        self.dfhack.disconnect()
        if HAS_COMMON_CLIENT:
            await super().disconnect(allow_autoreconnect)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Dwarfipelago — Dwarf Fortress AP client")
    parser.add_argument("--server",      default="archipelago.gg:38281", help="AP server address")
    parser.add_argument("--name",        default=None,                   help="Slot name")
    parser.add_argument("--password",    default=None,                   help="Room password")
    parser.add_argument("--dfhack-host", default=DFHACK_HOST,            help="DFHack host")
    parser.add_argument("--dfhack-port", default=DFHACK_PORT, type=int,  help="DFHack port")
    args = parser.parse_args()

    if not HAS_COMMON_CLIENT:
        logger.warning(
            "Archipelago CommonClient not found. Running in standalone mode "
            "(DFHack connection test only). Copy this file into your Archipelago "
            "installation to run with full AP support."
        )

    async def run():
        ctx = DwarfFortressContext(args.server, args.password)
        ctx.dfhack.host = args.dfhack_host
        ctx.dfhack.port = args.dfhack_port

        if args.name:
            ctx.auth = args.name

        tasks = [ctx.dfhack_poll_loop()]
        if HAS_COMMON_CLIENT:
            tasks.append(server_loop(ctx))

        await asyncio.gather(*tasks)

    asyncio.run(run())


if __name__ == "__main__":
    main()
