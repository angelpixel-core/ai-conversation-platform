"""Test template canónico para entrypoint del worker y lifecycle."""

from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest

from src.worker import main, run_worker
from src.worker_container import WorkerContainer


@pytest.mark.anyio
async def test_run_worker_starts_and_stops_on_cancellation() -> None:
    mock_container = MagicMock(spec=WorkerContainer)
    mock_container.start = AsyncMock()
    mock_container.stop = AsyncMock()

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_worker, mock_container)
        await anyio.sleep(0.01)
        tg.cancel_scope.cancel()

    mock_container.start.assert_awaited_once()
    mock_container.stop.assert_awaited_once()
