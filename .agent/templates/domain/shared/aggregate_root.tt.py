"""
Template canónico para la Clase Base AggregateRoot.
Reglas:
- Mantiene una colección interna privada de eventos de dominio (_domain_events).
- Permite registrar (record_event) y extraer (pull_events) eventos de forma atómica.
"""

from abc import ABC
from typing import Any, List


class AggregateRoot(ABC):
    """Clase base de infraestructura de dominio para acumulación de eventos."""

    def __init__(self) -> None:
        self._domain_events: List[Any] = []

    def record_event(self, event: Any) -> None:
        self._domain_events.append(event)

    def pull_events(self) -> List[Any]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
