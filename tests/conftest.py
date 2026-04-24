# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.tv.state import TVSettingsSnapshot, ChipGeneration


@pytest.fixture(autouse=True)
def patch_load_client_key(monkeypatch):
    """Prevent ConnectionManager.__init__ from touching the real system keychain."""
    monkeypatch.setattr("app.tv.connection.load_client_key", lambda ip: None)


@pytest.fixture
def mock_webos_client():
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.get_software_info = AsyncMock(return_value={
        "model_name": "OLED65C1PUB",
        "major_ver": "6",
        "minor_ver": "0",
    })
    client.client_key = "test-key-abc"
    return client


@pytest.fixture
def c2_mock_webos_client(mock_webos_client):
    mock_webos_client.get_software_info = AsyncMock(return_value={
        "model_name": "OLED65C2PUA",
        "major_ver": "7",
        "minor_ver": "0",
    })
    return mock_webos_client


@pytest.fixture
def sample_snapshot():
    return TVSettingsSnapshot(
        oled_light=70,
        contrast=85,
        chip_generation=ChipGeneration.ALPHA9_GEN4,
    )
