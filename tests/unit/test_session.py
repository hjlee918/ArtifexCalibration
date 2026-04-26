# tests/unit/test_session.py
import pytest
from unittest.mock import AsyncMock
from app.measurement.session import MeasurementSession, PatchResult
from app.measurement.patches import Patch, PatchSequence
from app.meter.device import XYZReading


@pytest.fixture
def mock_generator():
    gen = AsyncMock()
    gen.start = AsyncMock()
    gen.stop = AsyncMock()
    gen.set_patch = AsyncMock()
    return gen


@pytest.fixture
def mock_reader():
    reader = AsyncMock()
    reader.take_reading = AsyncMock(return_value=XYZReading(X=95.0, Y=100.0, Z=108.9))
    return reader


@pytest.fixture
def two_patch_seq():
    return PatchSequence("Test", [
        Patch(0, 0, 0, "Black"),
        Patch(255, 255, 255, "White"),
    ])


async def test_session_calls_generator_for_each_patch(mock_generator, mock_reader, two_patch_seq):
    session = MeasurementSession(generator=mock_generator, reader=mock_reader, sequence=two_patch_seq)
    await session.run()
    assert mock_generator.set_patch.call_count == 2


async def test_session_returns_patch_results(mock_generator, mock_reader, two_patch_seq):
    session = MeasurementSession(generator=mock_generator, reader=mock_reader, sequence=two_patch_seq)
    results = await session.run()
    assert len(results) == 2
    assert isinstance(results[0], PatchResult)
    assert results[0].patch.label == "Black"
    assert results[0].reading.Y == 100.0


async def test_session_calls_start_and_stop(mock_generator, mock_reader, two_patch_seq):
    session = MeasurementSession(generator=mock_generator, reader=mock_reader, sequence=two_patch_seq)
    await session.run()
    mock_generator.start.assert_called_once()
    mock_generator.stop.assert_called_once()


async def test_session_stop_called_on_error(mock_generator, mock_reader, two_patch_seq):
    mock_reader.take_reading = AsyncMock(side_effect=RuntimeError("meter disconnected"))
    session = MeasurementSession(generator=mock_generator, reader=mock_reader, sequence=two_patch_seq)
    with pytest.raises(RuntimeError, match="meter disconnected"):
        await session.run()
    mock_generator.stop.assert_called_once()


async def test_session_progress_callback(mock_generator, mock_reader, two_patch_seq):
    progress_calls = []
    session = MeasurementSession(
        generator=mock_generator, reader=mock_reader, sequence=two_patch_seq,
        on_progress=lambda i, total, result: progress_calls.append((i, total))
    )
    await session.run()
    assert progress_calls == [(1, 2), (2, 2)]


async def test_session_settle_time_is_zero_in_tests(mock_generator, mock_reader, two_patch_seq):
    # settle_time=0 to keep tests fast
    session = MeasurementSession(
        generator=mock_generator, reader=mock_reader, sequence=two_patch_seq, settle_time=0
    )
    results = await session.run()
    assert len(results) == 2
