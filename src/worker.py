"""Autonomous background worker entrypoint.

Runs a standalone worker process consuming events from RabbitMQ, executing
LLM chat completions, persisting assistant replies, and supporting graceful
POSIX signal shutdown (SIGINT, SIGTERM) via structured concurrency with AnyIO.
"""

import logging
import signal
import sys

import anyio

from src.worker_container import WorkerContainer, create_worker_container

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("worker")


async def run_worker(container: WorkerContainer) -> None:
    """Run the worker loop listening for shutdown signals.

    Args:
        container: Wired worker dependency container.
    """
    logger.info("Initializing worker container...")
    async with anyio.create_task_group() as tg:
        await container.start(task_group=tg)
        logger.info("Worker container running and listening for messages.")

        try:
            with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
                async for sig in signals:
                    logger.info(
                        "Received termination signal %s (%s). Starting graceful shutdown...",
                        sig.name,
                        sig.value,
                    )
                    break
        finally:
            logger.info("Stopping worker container...")
            with anyio.CancelScope(shield=True):
                await container.stop()
                tg.cancel_scope.cancel()
            logger.info("Worker container cleanly stopped.")


def main() -> None:
    """Entrypoint function for CLI / Docker execution."""
    container = create_worker_container()
    try:
        anyio.run(run_worker, container)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker process exited.")
    except Exception:
        logger.exception("Worker process encountered an unhandled fatal error.")
        sys.exit(1)


if __name__ == "__main__":
    main()
