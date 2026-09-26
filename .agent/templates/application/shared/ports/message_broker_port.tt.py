"""Template canónico para el Puerto de Message Broker (Application Port).

Reglas:
- Pertenece a src/application/shared/ports/.
- Abstracción para publicar mensajes/envelopes hacia un broker externo.
- Desacoplado de AMQP, RabbitMQ, Redis o Kafka.
"""

from abc import ABC, abstractmethod
from typing import Any


class MessageBrokerPort(ABC):
    """Puerto abstracto para publicación de mensajes estructurados en el broker."""

    @abstractmethod
    async def publish(self, topic: str, envelope: Any) -> None:
        """Publica un EventEnvelope en el topic o routing key especificado."""
        raise NotImplementedError
