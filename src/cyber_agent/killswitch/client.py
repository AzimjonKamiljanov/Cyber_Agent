"""Client for interacting with the Kill Switch service via Unix domain socket."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from cyber_agent.killswitch.service import get_socket_path

logger = logging.getLogger(__name__)


async def async_send_command(cmd: str, sock_path: Path | None = None) -> dict[str, Any]:
    target_sock = sock_path or get_socket_path()
    if not target_sock.exists():
        return {
            "error": f"Kill switch socket '{target_sock}' does not exist. Is the kill switch service running?",
        }

    try:
        reader, writer = await asyncio.open_unix_connection(str(target_sock))
        writer.write(cmd.strip().encode("utf-8") + b"\n")
        await writer.drain()

        resp_bytes = await reader.readline()
        writer.close()
        await writer.wait_closed()

        if not resp_bytes:
            return {"error": "Empty response from kill switch service"}

        return json.loads(resp_bytes.decode("utf-8"))  # type: ignore[no-any-return]
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to communicate with kill switch daemon: {e}"}


def send_command(cmd: str, sock_path: Path | None = None) -> dict[str, Any]:
    return asyncio.run(async_send_command(cmd, sock_path=sock_path))


def stop(sock_path: Path | None = None) -> dict[str, Any]:
    return send_command("STOP", sock_path=sock_path)


def resume(sock_path: Path | None = None) -> dict[str, Any]:
    return send_command("RESUME", sock_path=sock_path)


def status(sock_path: Path | None = None) -> dict[str, Any]:
    return send_command("STATUS", sock_path=sock_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cyber Agent Kill Switch Client")
    parser.add_argument(
        "command",
        choices=["stop", "resume", "status"],
        help="Command to issue (stop, resume, status)",
    )
    parser.add_argument(
        "--socket",
        type=Path,
        default=None,
        help="Optional path to killswitch.sock",
    )

    args = parser.parse_args()
    res = send_command(args.command.upper(), sock_path=args.socket)
    print(json.dumps(res, indent=2))
    if "error" in res:
        sys.exit(1)


if __name__ == "__main__":
    main()
