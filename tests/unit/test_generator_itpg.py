# tests/unit/test_generator_itpg.py
import pytest
from unittest.mock import AsyncMock
from app.generator.itpg import iTPGGenerator


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.start_itpg = AsyncMock(return_value={"returnValue": True})
    client.stop_itpg = AsyncMock(return_value={"returnValue": True})
    client.set_itpg_patch_color = AsyncMock(return_value={"returnValue": True})
    client.set_itpg_patch_window = AsyncMock(return_value={"returnValue": True})
    return client


@pytest.fixture
def gen(mock_client):
    return iTPGGenerator(client=mock_client)


async def test_start_calls_start_itpg(gen, mock_client):
    await gen.start()
    mock_client.start_itpg.assert_called_once()


async def test_start_calls_set_window(gen, mock_client):
    await gen.start()
    mock_client.set_itpg_patch_window.assert_called_once()


async def test_stop_calls_stop_itpg(gen, mock_client):
    await gen.stop()
    mock_client.stop_itpg.assert_called_once()


async def test_set_patch_converts_8bit_to_10bit(gen, mock_client):
    await gen.set_patch(r=128, g=64, b=255)
    mock_client.set_itpg_patch_color.assert_called_once()
    call_args = mock_client.set_itpg_patch_color.call_args[0]
    # 128/255 * 1023 ≈ 513
    assert 510 <= call_args[0] <= 516  # R
    # 64/255 * 1023 ≈ 256
    assert 253 <= call_args[1] <= 259  # G
    assert call_args[2] == 1023        # B (255/255 * 1023 = 1023)


async def test_set_patch_black(gen, mock_client):
    await gen.set_patch(r=0, g=0, b=0)
    args = mock_client.set_itpg_patch_color.call_args[0]
    assert args == (0, 0, 0)


async def test_set_patch_white(gen, mock_client):
    await gen.set_patch(r=255, g=255, b=255)
    args = mock_client.set_itpg_patch_color.call_args[0]
    assert args == (1023, 1023, 1023)


async def test_context_manager_starts_and_stops(mock_client):
    gen = iTPGGenerator(client=mock_client)
    async with gen:
        mock_client.start_itpg.assert_called_once()
    mock_client.stop_itpg.assert_called_once()
