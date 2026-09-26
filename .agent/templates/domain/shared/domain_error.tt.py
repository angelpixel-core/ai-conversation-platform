"""
Template canónico para Excepciones de Dominio (Domain Exception Base).
Reglas:
- Extiende de ValueError o Exception.
- Representa violaciones estrictas de reglas de negocio en la capa de dominio.
"""


class DomainError(ValueError):
    """Excepción base para violaciones de reglas de negocio."""

    pass
