"""
Template canónico para Pruebas de Integración del Adaptador HttpxClientAdapter.
"""

import pytest
from .httpx_client_adapter import HttpxClientAdapter


@pytest.mark.asyncio
async def test_httpx_client_adapter_instantiation() -> None:
    adapter = HttpxClientAdapter(timeout_seconds=5.0)
    assert adapter._timeout == 5.0
