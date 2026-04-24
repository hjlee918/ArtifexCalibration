# tests/unit/test_connection.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tv.connection import ConnectionManager
from app.tv.state import ChipGeneration


async def test_connect_stores_client_key(mock_webos_client):
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.save_client_key") as mock_save:
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        mock_save.assert_called_once_with("192.168.1.101", "test-key-abc")


async def test_connect_detects_c1_chip(mock_webos_client):
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.snapshot.chip_generation == ChipGeneration.ALPHA9_GEN4


async def test_connect_detects_c2_chip(c2_mock_webos_client):
    with patch("app.tv.connection.WebOsClient", return_value=c2_mock_webos_client), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.snapshot.chip_generation == ChipGeneration.ALPHA9_GEN5


async def test_connect_detects_c4_chip():
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.client_key = "key"
    mock_client.get_software_info = AsyncMock(return_value={
        "model_name": "OLED65C4PUA",
        "major_ver": "24",
        "minor_ver": "0",
    })
    with patch("app.tv.connection.WebOsClient", return_value=mock_client), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.snapshot.chip_generation == ChipGeneration.ALPHA9_GEN7


async def test_connect_unknown_model_returns_unknown():
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.client_key = "key"
    mock_client.get_software_info = AsyncMock(return_value={
        "model_name": "OLEDXXXNEW99",
        "major_ver": "99",
        "minor_ver": "0",
    })
    with patch("app.tv.connection.WebOsClient", return_value=mock_client), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.snapshot.chip_generation == ChipGeneration.UNKNOWN


async def test_firmware_warning_on_webos_73(mock_webos_client):
    mock_webos_client.get_software_info = AsyncMock(return_value={
        "model_name": "OLED65C1PUB",
        "major_ver": "7",
        "minor_ver": "3",
    })
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.firmware_warning is True


async def test_no_firmware_warning_on_webos_22(mock_webos_client):
    mock_webos_client.get_software_info = AsyncMock(return_value={
        "model_name": "OLED65C2PUA",
        "major_ver": "22",
        "minor_ver": "0",
    })
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.firmware_warning is False


async def test_uses_stored_client_key_on_reconnect(mock_webos_client):
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.load_client_key", return_value="stored-key"), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        assert mgr.client_key == "stored-key"
        await mgr.connect()
        assert mgr.client_key == "test-key-abc"


async def test_is_connected_false_before_connect():
    mgr = ConnectionManager("192.168.1.101")
    assert mgr.is_connected is False


async def test_is_connected_true_after_connect(mock_webos_client):
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.is_connected is True


async def test_disconnect_clears_client(mock_webos_client):
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        await mgr.disconnect()
        assert mgr.is_connected is False


# Pure function tests
def test_detect_chip_c1():
    from app.tv.connection import _detect_chip
    assert _detect_chip("OLED65C1PUB") == ChipGeneration.ALPHA9_GEN4

def test_detect_chip_c4():
    from app.tv.connection import _detect_chip
    assert _detect_chip("OLED83C4PSA") == ChipGeneration.ALPHA9_GEN7

def test_detect_chip_unknown():
    from app.tv.connection import _detect_chip
    assert _detect_chip("SAMSUNGNEO99") == ChipGeneration.UNKNOWN

def test_detect_chip_empty_string():
    from app.tv.connection import _detect_chip
    assert _detect_chip("") == ChipGeneration.UNKNOWN

def test_firmware_compat_7_2_is_safe():
    from app.tv.connection import _is_firmware_incompatible
    assert _is_firmware_incompatible("7", "2") is False

def test_firmware_compat_7_3_is_bad():
    from app.tv.connection import _is_firmware_incompatible
    assert _is_firmware_incompatible("7", "3") is True

def test_firmware_compat_6_x_is_safe():
    from app.tv.connection import _is_firmware_incompatible
    assert _is_firmware_incompatible("6", "0") is False

def test_firmware_compat_22_is_safe():
    from app.tv.connection import _is_firmware_incompatible
    assert _is_firmware_incompatible("22", "0") is False

async def test_reconnect_with_backoff_succeeds_on_retry(mock_webos_client):
    call_count = 0
    original_connect = mock_webos_client.connect

    async def fail_first_then_succeed():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("first attempt fails")
        await original_connect()

    mock_webos_client.connect = fail_first_then_succeed
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.save_client_key"), \
         patch("app.tv.connection.asyncio.sleep"):
        mgr = ConnectionManager("192.168.1.101")
        result = await mgr.reconnect_with_backoff(max_attempts=3)
    assert result is True

async def test_reconnect_with_backoff_returns_false_when_exhausted(mock_webos_client):
    mock_webos_client.connect = AsyncMock(side_effect=ConnectionError("always fails"))
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.save_client_key"), \
         patch("app.tv.connection.asyncio.sleep"):
        mgr = ConnectionManager("192.168.1.101")
        result = await mgr.reconnect_with_backoff(max_attempts=3)
    assert result is False
