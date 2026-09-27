"""Unit tests for standalone worker entrypoint and graceful shutdown lifecycle."""

from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest

from src.worker import main, run_worker
from src.worker_container import WorkerContainer


@pytest.mark.anyio
async def test_run_worker_starts_and_stops_on_cancellation() -> None:
    # Arrange
    mock_container = MagicMock(spec=WorkerContainer)
    mock_container.start = AsyncMock()
    mock_container.stop = AsyncMock()

    # Act: Run worker inside a task group that cancels it shortly after starting
    async with anyio.create_task_group() as tg:
        tg.start_soon(run_worker, mock_container)
        await anyio.sleep(0.01)
        tg.cancel_scope.cancel()

    # Assert
    mock_container.start.assert_awaited_once()
    mock_container.stop.assert_awaited_once()


def test_main_invokes_container_and_anyio_run() -> None:
    mock_container = MagicMock(spec=WorkerContainer)
    with (
        patch("src.worker.create_worker_container", return_value=mock_container) as mock_create,
        patch("src.worker.anyio.run") as mock_anyio_run,
    ):
        main()

        mock_create.assert_called_once()
        mock_anyio_run.assert_called_once_with(run_worker, mock_container)


def test_main_handles_fatal_exception_and_exits() -> None:
    mock_container = MagicMock(spec=WorkerContainer)
    with (
        patch("src.worker.create_worker_container", return_value=mock_container),
        patch("src.worker.anyio.run", side_effect=RuntimeError("Fatal error")),
        patch("src.worker.sys.exit") as mock_exit,
    ):
        main()
        mock_exit.assert_called_once_with(1)


def test_main_handles_keyboard_interrupt_gracefully() -> None:
    mock_container = MagicMock(spec=WorkerContainer)
    with (
        patch("src.worker.create_worker_container", return_value=mock_container),
        patch("src.worker.anyio.run", side_effect=KeyboardInterrupt),
    ):
        main()  # Should not raise or sys.exit(1)


@pytest.mark.anyio
async def test_run_worker_handles_signal_gracefully() -> None:
    from unittest.mock import MagicMock

    mock_container = MagicMock(spec=WorkerContainer)
    mock_container.start = AsyncMock()
    mock_container.stop = AsyncMock()

    mock_sig = MagicMock()
    mock_sig.name = "SIGINT"
    mock_sig.value = 2

    class AsyncSignalStream:
        async def __aiter__(self):
            yield mock_sig

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    with patch("src.worker.anyio.open_signal_receiver", return_value=AsyncSignalStream()):
        await run_worker(mock_container)

    mock_container.start.assert_awaited_once()
    mock_container.stop.assert_awaited_once()
