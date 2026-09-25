"""
Template canónico para una Entidad Agregada (Aggregate Root) en Python.
Reglas:
- Extiende de AggregateRoot para gestionar eventos de dominio.
- Constructor privado o protegido; instanciación pública vía factory methods (cls.create).
- Métodos de negocio explícitos que validan invariantes antes de mutar el estado.
- Sin dependencias de frameworks ni librerías de persistencia.
"""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID, uuid4


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


class DomainValidationError(ValueError):
    """Lanzada cuando se violan reglas o invariantes de negocio."""

    pass


@dataclass(frozen=True)
class ExampleItemCreatedDomainEvent:
    aggregate_id: UUID
    occurred_on: datetime


class ExampleEntity(AggregateRoot):
    def __init__(
        self,
        entity_id: UUID,
        name: str,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self._id = entity_id
        self._name = self._validate_name(name)
        self._created_at = created_at

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @classmethod
    def create(cls, name: str, entity_id: Optional[UUID] = None) -> "ExampleEntity":
        eid = entity_id or uuid4()
        now = datetime.now(timezone.utc)

        instance = cls(
            entity_id=eid,
            name=name,
            created_at=now,
        )

        instance.record_event(
            ExampleItemCreatedDomainEvent(
                aggregate_id=eid,
                occurred_on=now,
            )
        )
        return instance

    def rename(self, new_name: str) -> None:
        self._name = self._validate_name(new_name)

    @staticmethod
    def _validate_name(name: str) -> str:
        clean = name.strip() if name else ""
        if not clean:
            raise DomainValidationError("El nombre no puede estar vacío.")
        if len(clean) > 100:
            raise DomainValidationError("El nombre excede el límite de 100 caracteres.")
        return clean
