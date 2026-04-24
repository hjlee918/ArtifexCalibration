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

def test_discovered_tv_name_falls_back_to_ip():
    # When FRIENDLY-NAME header is absent, name should default to the IP
    data = (
        "HTTP/1.1 200 OK\r\n"
        "LOCATION: http://192.168.1.200:3000/\r\n"
        "USN: uuid:xyz\r\n\r\n"
    ).encode()
    from app.tv.discovery import _parse_ssdp_response
    parsed = _parse_ssdp_response(data)
    ip = parsed.get("_IP", "")
    name = parsed.get("FRIENDLY-NAME", ip)
    assert name == "192.168.1.200"

async def test_discover_deduplicates_by_ip():
    # Two responses from the same IP should produce only one DiscoveredTV
    mock_sock = MagicMock()
    mock_sock.recvfrom = MagicMock(side_effect=[
        (SSDP_RESPONSE, ("192.168.1.101", 1900)),
        (SSDP_RESPONSE, ("192.168.1.101", 1900)),  # duplicate
        TimeoutError(),
    ])
    with patch("app.tv.discovery.socket.socket", return_value=mock_sock):
        tvs = await discover_tvs(timeout=0.1)
    assert len(tvs) == 1
