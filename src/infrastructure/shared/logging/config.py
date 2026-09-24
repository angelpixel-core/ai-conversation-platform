import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure a small structured-friendly baseline logger.

    Production can replace this with JSON logging without touching domain code.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
