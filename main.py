"""Application entry point for the crypto-monitor services.

The default mode starts the database and asynchronous risk-event logger and
keeps the process alive until SIGINT/SIGTERM.  ``--once`` is useful for smoke
checks and container health probes.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from contextlib import suppress

from audit.ledger import close_db, init_db
from events import init_event_logger, shutdown_event_logger

LOGGER = logging.getLogger(__name__)


async def run(*, once: bool = False) -> None:
    """Initialize application resources and run until shutdown is requested."""
    init_db()
    await init_event_logger()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_shutdown() -> None:
        LOGGER.info("Shutdown requested")
        stop_event.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(signum, request_shutdown)

    try:
        if not once:
            await stop_event.wait()
    finally:
        await shutdown_event_logger()
        close_db()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crypto mining monitor")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Initialize and shut down immediately (useful for smoke tests)",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    try:
        asyncio.run(run(once=args.once))
    except KeyboardInterrupt:
        # SIGINT is normally handled by the event loop; this covers platforms
        # where add_signal_handler is unavailable.
        LOGGER.info("Interrupted")


if __name__ == "__main__":
    main()
