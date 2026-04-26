# tests/unit/test_generator_pgenerator.py
import pytest
from contextlib import asynccontextmanager
from unittest.mock import patch, AsyncMock, MagicMock
from app.generator.pgenerator import PGeneratorClient


@pytest.fixture
def gen():
    return PGeneratorClient(host="192.168.1.200", port=8080)


def _make_session_mock(get_return_value):
    """Create a mock session object with a proper async context manager for get()."""
    session = MagicMock()
    session.get.return_value = get_return_value
    return session


async def test_set_patch_sends_http_get(gen):
    mock_resp = MagicMock()
    mock_resp.status = 200

    @asynccontextmanager
    async def mock_get(*args, **kwargs):
        yield mock_resp

    with patch("app.generator.pgenerator.aiohttp.ClientSession") as mock_cls:
        mock_session = _make_session_mock(mock_get())
        mock_cls.return_value.__aenter__.return_value = mock_session

        await gen.set_patch(r=128, g=64, b=255)
        mock_session.get.assert_called_once()
        url = mock_session.get.call_args[0][0]
        assert "r=128" in url
        assert "g=64" in url
        assert "b=255" in url


async def test_set_patch_http_error_raises(gen):
    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.text = AsyncMock(return_value="Internal Error")

    @asynccontextmanager
    async def mock_get(*args, **kwargs):
        yield mock_resp

    with patch("app.generator.pgenerator.aiohttp.ClientSession") as mock_cls:
        mock_session = _make_session_mock(mock_get())
        mock_cls.return_value.__aenter__.return_value = mock_session

        with pytest.raises(RuntimeError, match="PGenerator HTTP error"):
            await gen.set_patch(r=128, g=64, b=255)


async def test_probe_returns_true_on_200(gen):
    mock_resp = MagicMock()
    mock_resp.status = 200

    @asynccontextmanager
    async def mock_get(*args, **kwargs):
        yield mock_resp

    with patch("app.generator.pgenerator.aiohttp.ClientSession") as mock_cls:
        mock_session = _make_session_mock(mock_get())
        mock_cls.return_value.__aenter__.return_value = mock_session

        assert await gen.probe() is True


async def test_probe_returns_false_on_connection_error(gen):
    import aiohttp

    @asynccontextmanager
    async def mock_get(*args, **kwargs):
        raise aiohttp.ClientError()
        yield  # pragma: no cover

    with patch("app.generator.pgenerator.aiohttp.ClientSession") as mock_cls:
        mock_session = _make_session_mock(mock_get())
        mock_cls.return_value.__aenter__.return_value = mock_session

        assert await gen.probe() is False


async def test_start_is_noop(gen):
    await gen.start()  # should not raise


async def test_stop_sends_black_patch(gen):
    with patch.object(gen, "set_patch", AsyncMock()) as mock_set:
        await gen.stop()
        mock_set.assert_called_once_with(0, 0, 0)
