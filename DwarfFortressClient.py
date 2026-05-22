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

# DFHack protobuf wire protocol constants
DFHACK_MAGIC_REQUEST  = b"DFHack?\n"
DFHACK_MAGIC_REPLY    = b"DFHack!\n"
DFHACK_METHOD_BIND    = 0   # BindMethod
DFHACK_METHOD_RUN_CMD = 1   # RunCommand


class DFHackConnection:
    """
    Minimal DFHack remote API client.

    Implements only what Dwarfipelago needs:
    - RunCommand: execute a DFHack Lua script / console command
    - Read the pending-checks queue written by the Lua mod
    """

    def __init__(self, host: str = DFHACK_HOST, port: int = DFHACK_PORT):
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None

    def connect(self) -> bool:
        try:
            sock = socket.create_connection((self.host, self.port), timeout=5)
            # Exchange magic bytes
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

    def is_connected(self) -> bool:
        return self._sock is not None

    def run_command(self, command: str) -> Optional[str]:
        """
        Execute a DFHack console command (including Lua scripts) via RunCommand RPC.
        Returns the text output, or None on failure.

        Note: Full protobuf encoding is TODO — this is a placeholder that logs
        the intended call. Wire protocol details:
        https://docs.dfhack.org/en/stable/docs/dev/Remote.html
        """
        if not self._sock:
            return None
        # TODO: encode RunCommand protobuf message and send over self._sock
        # For now, log the intended command for development reference.
        logger.debug(f"[DFHack] run_command: {command}")
        return None

    def pop_pending_checks(self) -> list[int]:
        """
        Read and clear the pending-checks queue written by the Lua mod.
        The Lua mod writes to dfhack.persistent site data key "dwarfipelago/pending_checks".
        We read it via a RunCommand that prints the JSON, then clears the queue.
        Returns a list of AP location IDs.
        """
        # TODO: implement once RunCommand wire protocol is complete.
        # Command to run in DFHack:
        #   local q = dfhack.persistent.getSiteData("dwarfipelago/pending_checks") or "[]"
        #   dfhack.persistent.setSiteData("dwarfipelago/pending_checks", "[]")
        #   print(q)
        return []

    def deliver_item(self, item_name: str):
        """
        Deliver a received AP item to the fortress by calling the Lua item handler.
        """
        # Escape the item name for safe embedding in Lua string
        safe_name = item_name.replace("\\", "\\\\").replace('"', '\\"')
        cmd = f'require("dwarfipelago.items").receive("{safe_name}")'
        self.run_command(f'lua {cmd}')
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
        self._poll_interval = 5.0  # seconds between fortress state polls
        self._received_index = 0   # last applied item index

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
                await self._process_new_checks()
                await self._apply_pending_items()
            except Exception as e:
                logger.warning(f"DFHack poll error: {e}")
                self.dfhack.disconnect()

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
            item_name = self.item_names.lookup_in_game(network_item.item) if hasattr(self, 'item_names') else str(network_item.item)
            await asyncio.get_event_loop().run_in_executor(
                None, self.dfhack.deliver_item, item_name
            )
            self._received_index = i + 1
            # Persist index in case we restart mid-session
            self.dfhack.run_command(
                f'dfhack.persistent.setSiteData("dwarfipelago/received_index", "{self._received_index}")'
            )

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
    parser.add_argument("--server",   default="archipelago.gg:38281", help="AP server address")
    parser.add_argument("--name",     default=None,                   help="Slot name")
    parser.add_argument("--password", default=None,                   help="Room password")
    parser.add_argument("--dfhack-host", default=DFHACK_HOST,         help="DFHack host")
    parser.add_argument("--dfhack-port", default=DFHACK_PORT, type=int, help="DFHack port")
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
