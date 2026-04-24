# app/tv/discovery.py
import asyncio
import socket
import re
from dataclasses import dataclass

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_MX = 3
SSDP_ST = "urn:lge-com:service:webos-second-screen:1"

SSDP_REQUEST = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
    "MAN: \"ssdp:discover\"\r\n"
    f"MX: {SSDP_MX}\r\n"
    f"ST: {SSDP_ST}\r\n"
    "\r\n"
).encode()


@dataclass
class DiscoveredTV:
    ip: str
    name: str


def _parse_ssdp_response(data: bytes) -> dict:
    text = data.decode(errors="ignore")
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip().upper()] = value.strip()
    ip_match = re.search(r"http://(\d+\.\d+\.\d+\.\d+)", result.get("LOCATION", ""))
    result["_IP"] = ip_match.group(1) if ip_match else ""
    return result


def _sync_discover(timeout: float) -> list[DiscoveredTV]:
    """Blocking socket scan — call via run_in_executor to avoid blocking the event loop."""
    found: dict[str, DiscoveredTV] = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(timeout)
    try:
        sock.sendto(SSDP_REQUEST, (SSDP_ADDR, SSDP_PORT))
        while True:
            try:
                data, _ = sock.recvfrom(4096)
                parsed = _parse_ssdp_response(data)
                ip = parsed.get("_IP", "")
                name = parsed.get("FRIENDLY-NAME", ip)
                if ip and ip not in found:
                    found[ip] = DiscoveredTV(ip=ip, name=name)
            except TimeoutError:
                break
    finally:
        sock.close()
    return list(found.values())


async def discover_tvs(timeout: float = 5.0) -> list[DiscoveredTV]:
    """Discover LG webOS TVs on the local network via SSDP M-SEARCH.

    Non-blocking: socket I/O runs in a thread pool executor so the event loop
    stays responsive during the scan.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_discover, timeout)
