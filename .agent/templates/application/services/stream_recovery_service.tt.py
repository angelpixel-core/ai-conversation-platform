"""Template canónico para StreamRecoveryService (Application Service).

Reglas:
- Pertenece a src/application/conversations/services/.
- Orquesta la recuperación y transmisión continua de chunks perdidos para clientes reconectados.
- Utiliza AnyIO para control de pausas, reintentos y concurrencia estructurada.
"""

from collections.abc import AsyncIterator
import logging

import anyio

from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.domain.conversations.value_objects.stream_chunk import StreamChunk

logger = logging.getLogger(__name__)


class StreamRecoveryService:
    """Servicio de aplicación para reanudar la emisión de streams interrumpidos."""

    def __init__(
        self,
        buffer_repo: StreamBufferRepositoryPort,
        poll_interval_seconds: float = 0.05,
        max_wait_seconds: float = 30.0,
    ) -> None:
        self._buffer_repo = buffer_repo
        self._poll_interval = poll_interval_seconds
        self._max_wait = max_wait_seconds

    async def recover_stream(
        self,
        stream_id: str,
        since_sequence: int = -1,
    ) -> AsyncIterator[StreamChunk]:
        """Generador asíncrono que emite chunks pendientes y continúa emitiendo en vivo hasta que el stream finalice."""
        current_seq = since_sequence
        elapsed = 0.0

        while True:
            # 1. Recuperar chunks nuevos generados
            new_chunks = await self._buffer_repo.get_chunks_since(
                stream_id=stream_id,
                since_sequence=current_seq,
            )

            for chunk in new_chunks:
                yield chunk
                current_seq = max(current_seq, chunk.sequence_number)
                elapsed = 0.0  # Reset timeout al recibir actividad

                if chunk.is_final:
                    logger.info(
                        "Stream %s completó su transmisión final con secuencia %d",
                        stream_id,
                        current_seq,
                    )
                    return

            # 2. Si ya está completado en base de datos sin más chunks pendientes, salir
            if await self._buffer_repo.is_stream_completed(stream_id):
                return

            # 3. Esperar al siguiente lote con AnyIO
            await anyio.sleep(self._poll_interval)
            elapsed += self._poll_interval

            if elapsed >= self._max_wait:
                logger.warning(
                    "Tiempo de espera agotado (%ss) esperando actividad en stream %s",
                    self._max_wait,
                    stream_id,
                )
                break
