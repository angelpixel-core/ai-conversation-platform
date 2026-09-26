"""
Template canónico para el Composition Root (src/main.py).
Reglas:
- Instancia y enlaza los adaptadores concretos con los puertos y handlers de la aplicación.
- Retorna la instancia configurada de FastAPI (o aplicación web).
"""

from fastapi import FastAPI

from src.interfaces.http.api import build_api


def create_app() -> FastAPI:
    """Construye y enlaza las dependencias de la aplicación."""
    # Wire handlers & repositories
    # handler = CreateConversationHandler(...)
    # return build_api(handler=handler)
    pass


app = create_app()
