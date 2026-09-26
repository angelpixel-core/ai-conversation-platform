"""
Template canónico para Endpoints de Streaming HTTP en FastAPI (Server-Sent Events / SSE).
Reglas:
- Utiliza StreamingResponse de fastapi.responses con media_type="text/event-stream".
- Retorna un generador asíncrono con formato SSE data: ...\n\n.
- Maneja desconexiones del cliente de forma limpia.
"""

from typing import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/conversations", tags=["Messaging & Streaming"])


async def generate_sse_stream(conversation_id: UUID) -> AsyncIterator[str]:
    """Generador asíncrono que formatea tokens para protocolo SSE."""
    try:
        tokens = ["Hola", ", ", "este ", "es ", "un ", "stream ", "SSE."]
        for token in tokens:
            # Formato estándar Server-Sent Events (SSE)
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        yield f"data: [ERROR] {str(exc)}\n\n"


@router.get(
    "/{conversation_id}/stream",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Canal reactivo SSE para transmisión token a token del LLM",
)
async def stream_conversation(conversation_id: UUID) -> StreamingResponse:
    """Abre un canal SSE de streaming token a token."""
    return StreamingResponse(
        generate_sse_stream(conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
