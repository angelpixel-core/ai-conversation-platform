"""Template canónico para el Puerto de Consumo de Eventos (EventConsumerPort).

Reglas:
- Pertenece a src/application/shared/ports/.
- Abstracción para suscribir handlers a tópicos/colas y orquestar el consumo de mensajes.
- Desacoplado de AMQP, RabbitMQ o Redis.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any


class EventConsumerPort(ABC):
    """Puerto abstracto para suscripción y consumo asíncrono de eventos."""

    @abstractmethod
    def register_handler(
        self,
        topic: str,
        handler: Callable[[Any], Awaitable[None]],
    ) -> None:
        """Registra una función manejadora para un topic específico."""
        raise NotImplementedError

    @abstractmethod
    async def start_consuming(self) -> None:
        """Inicia el bucle de consumo de eventos del broker."""
        raise NotImplementedError

    @abstractmethod
    async def stop_consuming(self) -> None:
        """Detiene de forma ordenada el consumo de eventos."""
        raise NotImplementedError
