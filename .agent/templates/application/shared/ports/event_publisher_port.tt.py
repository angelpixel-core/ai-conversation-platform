"""
Template canónico para el Puerto Secundario de Publicación de Eventos (EventPublisherPort).
Reglas:
- Definido en la capa de aplicación como contrato abstracto (ABC).
- No depende de Message Brokers específicos (RabbitMQ, Kafka, Redis PubSub).
"""

from abc import ABC, abstractmethod
from typing import Any


class EventPublisherPort(ABC):
    """Puerto abstracto para publicación de eventos de integración o dominio."""

    @abstractmethod
    async def publish(self, event: Any) -> None:
        """Publica un evento hacia el bus de mensajes o dispatcher."""
        pass
