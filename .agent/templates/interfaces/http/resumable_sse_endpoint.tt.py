"""Template canónico para Resumable SSE Streaming Endpoint en FastAPI (Driver Adapter).

Reglas:
- Pertenece a src/interfaces/http/.
- Lee el encabezado estándar HTTP Last-Event-ID para soportar reconexiones transparentes.
- Genera eventos con formato SSE: id, event y data.
"""

from collections.abc import AsyncIterator
import json
from typing import Annotated

from fastapi import Header, HTTPException, status
from fastapi.responses import StreamingResponse

from src.application.services.stream_recovery_service import StreamRecoveryService
from src.domain.conversations.value_objects.stream_chunk import StreamChunk


def format_sse_chunk(chunk: StreamChunk) -> str:
    """Formatea un StreamChunk como un evento Server-Sent Events estándar."""
    data = json.dumps({"content": chunk.content, "is_final": chunk.is_final})
    return f"id: {chunk.sequence_number}\nevent: message\ndata: {data}\n\n"


def parse_last_event_id(raw_header: str | None) -> int:
    """Convierte el header Last-Event-ID a secuencia entera, retornando -1 si no está presente."""
    if not raw_header:
        return -1
    try:
        seq = int(raw_header.strip())
        if seq < 0:
            raise ValueError
        return seq
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Encabezado 'Last-Event-ID' inválido: '{raw_header}'. Debe ser un entero no negativo.",
        ) from exc


async def build_resumable_sse_response(
    stream_id: str,
    recovery_service: StreamRecoveryService,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """Crea una respuesta StreamingResponse SSE con soporte de reanudación automática."""
    since_sequence = parse_last_event_id(last_event_id)

    async def event_generator() -> AsyncIterator[str]:
        async for chunk in recovery_service.recover_stream(
            stream_id=stream_id,
            since_sequence=since_sequence,
        ):
            yield format_sse_chunk(chunk)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
