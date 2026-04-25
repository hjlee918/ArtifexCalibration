# tests/unit/test_dv_config.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock
from app.tv.dv_config import DolbyVisionConfig, load_dv_config

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_load_dv_config_parses_file():
    cfg = load_dv_config(FIXTURES / "test_dv_config.txt")
    assert isinstance(cfg, DolbyVisionConfig)
    assert len(cfg.raw_text) > 0


def test_load_dv_config_wrong_extension_raises():
    with pytest.raises(ValueError, match="Expected .txt or .cfg"):
        load_dv_config(Path("file.xyz"))


async def test_upload_dv_config_sends_ssap():
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value={"returnValue": True})
    cfg = DolbyVisionConfig(raw_text="[DisplayConfiguration]\nVersion=2\n")
    await cfg.upload(mock_client)
    mock_client.request.assert_called_once()
    uri, payload = mock_client.request.call_args[0]
    assert "dolby" in uri.lower() or "externalpq" in uri.lower() or "dv" in uri.lower()


async def test_upload_dv_config_failure_raises():
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value={"returnValue": False,
                                                    "errorText": "not supported"})
    cfg = DolbyVisionConfig(raw_text="[DisplayConfiguration]\n")
    with pytest.raises(RuntimeError, match="not supported"):
        await cfg.upload(mock_client)


def test_dv_config_raw_text_stored():
    cfg = DolbyVisionConfig(raw_text="test content")
    assert cfg.raw_text == "test content"
