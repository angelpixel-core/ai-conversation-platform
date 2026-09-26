"""
Template canónico para Pruebas de Configuración de Logging.
"""

from .logging_config import configure_logging


def test_configure_logging_executes_without_errors() -> None:
    configure_logging(log_level="DEBUG")
