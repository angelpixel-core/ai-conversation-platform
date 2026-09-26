"""
Template canónico para Pruebas Unitarias de Excepciones de Dominio.
"""

import pytest
from src.domain.shared.domain_error import DomainError


def test_domain_error_raises_with_message() -> None:
    with pytest.raises(DomainError, match="Regla violada"):
        raise DomainError("Regla violada")
