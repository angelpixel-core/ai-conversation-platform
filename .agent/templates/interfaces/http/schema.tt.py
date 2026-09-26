# .agent/templates/http-routers/python/schema.template.py
"""
Template canónico para Esquemas HTTP / DTOs en Python con Pydantic v2.
Reglas:
- Pertenece a src/interfaces/http/.
- Separa estrictamente el Request del Response.
- Usa tipos primitivos y modelos de Pydantic con validación declarativa.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CreateExampleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nombre descriptivo")
    custom_id: Optional[UUID] = Field(None, description="Identificador único opcional")


class ExampleResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
