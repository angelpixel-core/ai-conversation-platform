"""
Template canónico para Configuración de Logging Estructurado.
Reglas:
- Configura formateadores de logs estandarizados (JSON o texto estructurado).
- Centraliza la captura de logs en toda la aplicación.
"""

import logging


def configure_logging(log_level: str = "INFO") -> None:
    """Configura el sistema de logging global."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )
