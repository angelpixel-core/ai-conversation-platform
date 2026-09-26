"""
Template canónico para la Capa de Telemetría y Métricas.
Reglas:
- Abstracción neutra para métricas y trazas (Prometheus / OpenTelemetry).
"""


class TelemetryService:
    """Servicio de infraestructura para emisión de métricas de negocio."""

    def record_counter(self, metric_name: str, value: int = 1) -> None:
        pass
