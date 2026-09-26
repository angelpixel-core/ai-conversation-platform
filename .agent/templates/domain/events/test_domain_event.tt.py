"""
Template canónico para Pruebas Unitarias de Eventos de Dominio.
Reglas:
- Verifica la estructura inmutable de los datos del evento y la marca de tiempo de ocurrencia.
"""

from uuid import uuid4
from datetime import datetime, timezone
import pytest

from .domain_event import ExampleDomainEvent


def test_domain_event_structure_and_timestamp() -> None:
    # Arrange
    aggregate_id = uuid4()

    # Act
    event = ExampleDomainEvent(aggregate_id=aggregate_id)

    # Assert
    assert event.aggregate_id == aggregate_id
    assert event.occurred_at is not None
    assert isinstance(event.occurred_at, datetime)
