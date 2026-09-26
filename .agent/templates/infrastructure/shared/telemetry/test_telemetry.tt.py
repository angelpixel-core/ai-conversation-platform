"""
Template canónico para Pruebas del Servicio de Telemetría.
"""

from .telemetry import TelemetryService


def test_telemetry_records_metrics() -> None:
    service = TelemetryService()
    service.record_counter("conversations_created_total", 1)
