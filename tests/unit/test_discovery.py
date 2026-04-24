# tests/unit/test_discovery.py
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.tv.discovery import DiscoveredTV, discover_tvs

def test_discovered_tv_has_ip_and_name():
    tv = DiscoveredTV(ip="192.168.1.101", name="[LG] webOS TV OLED65C1")
    assert tv.ip == "192.168.1.101"
    assert tv.name == "[LG] webOS TV OLED65C1"

SSDP_RESPONSE = (
    "HTTP/1.1 200 OK\r\n"
    "LOCATION: http://192.168.1.101:3000/\r\n"
    "FRIENDLY-NAME: [LG] webOS TV OLED65C1\r\n"
    "USN: uuid:abc123\r\n\r\n"
).encode()

async def test_discover_returns_found_tvs():
    mock_sock = MagicMock()
    mock_sock.recvfrom = MagicMock(side_effect=[
        (SSDP_RESPONSE, ("192.168.1.101", 1900)),
        TimeoutError(),
    ])
    with patch("app.tv.discovery.socket.socket", return_value=mock_sock):
        tvs = await discover_tvs(timeout=0.1)
    assert len(tvs) == 1
    assert tvs[0].ip == "192.168.1.101"
    assert "C1" in tvs[0].name

async def test_discover_returns_empty_on_timeout():
    mock_sock = MagicMock()
    mock_sock.recvfrom = MagicMock(side_effect=TimeoutError())
    with patch("app.tv.discovery.socket.socket", return_value=mock_sock):
        tvs = await discover_tvs(timeout=0.1)
    assert tvs == []
