"""
Template canónico para un Evento de Dominio (Domain Event).
Reglas:
- Inmutable (@dataclass(frozen=True)).
- Contiene datos relevantes del hecho ocurrido en el pasado.
- Incluye timestamp de ocurrencia (occurred_at en UTC).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class ExampleDomainEvent:
    aggregate_id: UUID
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
