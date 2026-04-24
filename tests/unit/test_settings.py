# tests/unit/test_settings.py
import pytest
from unittest.mock import AsyncMock
from app.tv.settings import LGTVSettings


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.request = AsyncMock(return_value={"returnValue": True})
    return client


@pytest.fixture
def settings(mock_client):
    return LGTVSettings(client=mock_client, pic_mode="expert1")


async def test_set_white_balance_2pt(settings, mock_client):
    await settings.set_white_balance_2pt(
        red_gain=10, green_gain=0, blue_gain=-5,
        red_offset=0, green_offset=0, blue_offset=0
    )
    mock_client.request.assert_called_once()
    uri, payload = mock_client.request.call_args[0]
    assert uri == "ssap://externalpq/setExternalPqData"
    assert payload["picMode"] == "expert1"
    assert payload["data"]["whiteBalanceRedGain"] == 10
    assert payload["data"]["whiteBalanceBlueGain"] == -5


async def test_set_white_balance_20pt(settings, mock_client):
    red = [0] * 20
    green = [0] * 20
    blue = [5] * 20
    await settings.set_white_balance_20pt(red=red, green=green, blue=blue)
    mock_client.request.assert_called_once()
    uri, payload = mock_client.request.call_args[0]
    assert uri == "ssap://externalpq/setExternalPqData"
    assert len(payload["data"]["whiteBalance20ptBlue"]) == 20
    assert payload["data"]["whiteBalance20ptBlue"][0] == 5


async def test_set_white_balance_20pt_wrong_length_raises(settings):
    with pytest.raises(ValueError, match="20 values"):
        await settings.set_white_balance_20pt(red=[0]*10, green=[0]*20, blue=[0]*20)


async def test_set_cms_color(settings, mock_client):
    await settings.set_cms_color("red", hue=5, saturation=-3, luminance=0)
    mock_client.request.assert_called_once()
    uri, payload = mock_client.request.call_args[0]
    assert uri == "ssap://externalpq/setExternalPqData"
    assert payload["data"]["colorManagementRedHue"] == 5
    assert payload["data"]["colorManagementRedSaturation"] == -3


async def test_set_cms_all_colors(settings, mock_client):
    for color in ("red", "green", "blue", "cyan", "magenta", "yellow"):
        mock_client.request.reset_mock()
        await settings.set_cms_color(color, hue=1, saturation=2, luminance=3)
        mock_client.request.assert_called_once()


async def test_set_cms_invalid_color_raises(settings):
    with pytest.raises(ValueError, match="Unknown color"):
        await settings.set_cms_color("purple", hue=0, saturation=0, luminance=0)


async def test_set_dynamic_contrast(settings, mock_client):
    await settings.set_dynamic_contrast("medium")
    mock_client.request.assert_called_once()
    _, payload = mock_client.request.call_args[0]
    assert payload["data"]["dynamicContrast"] == "medium"


async def test_ssap_error_raises(mock_client):
    mock_client.request = AsyncMock(return_value={"returnValue": False, "errorText": "not supported"})
    s = LGTVSettings(client=mock_client, pic_mode="expert1")
    with pytest.raises(RuntimeError, match="not supported"):
        await s.set_dynamic_contrast("low")
