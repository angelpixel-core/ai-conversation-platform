# .agent/templates/http-routers/python/router.template.py
"""
Template canónico para un Router HTTP en FastAPI.
Reglas:
- Mapea el Request HTTP hacia el Command de Aplicación.
- Inyecta el CommandHandler mediante Depends() o el contenedor IoC.
- Devuelve códigos de estado HTTP precisos (201 Created para escrituras).
"""

from fastapi import APIRouter, Depends, status
from src.container import Container, container
from src.application.example.commands.create_example_command import CreateExampleCommand
from src.interfaces.http.schema.template import CreateExampleRequest, ExampleResponse

router = APIRouter(prefix="/examples", tags=["Examples"])


def get_create_example_handler():
    return container.create_example_command_handler


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ExampleResponse,
    summary="Crea un nuevo recurso de ejemplo",
)
async def create_example_endpoint(
    payload: CreateExampleRequest,
    handler=Depends(get_create_example_handler),
):
    command = CreateExampleCommand(
        name=payload.name,
        custom_id=payload.custom_id,
    )
    result = await handler.handle(command)
    return {"id": result.entity_id, "name": payload.name, "created_at": "..."}
