# app/generator/pgenerator.py
# VERIFY: _PATCH_PATH endpoint against your PGenerator 1.6 installation.
# Open http://<pi-ip>:8080/ in a browser to confirm the API path.
from __future__ import annotations
import aiohttp
from app.generator.base import PatternGenerator

_PATCH_PATH = "/patch"


class PGeneratorClient(PatternGenerator):
    """PGenerator 1.6 HTTP API client for Raspberry Pi 4."""

    def __init__(self, host: str, port: int = 8080):
        self.host = host
        self.port = port
        self._base_url = f"http://{host}:{port}"

    async def start(self) -> None:
        pass  # PGenerator is always running; no explicit start needed

    async def stop(self) -> None:
        await self.set_patch(0, 0, 0)

    async def set_patch(self, r: int, g: int, b: int) -> None:
        """Send HTTP GET to display an 8-bit RGB patch."""
        url = f"{self._base_url}{_PATCH_PATH}?r={r}&g={g}&b={b}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(
                        f"PGenerator HTTP error {resp.status} for patch ({r},{g},{b}): {text}"
                    )

    async def probe(self) -> bool:
        """Return True if PGenerator is reachable."""
        try:
            url = f"{self._base_url}{_PATCH_PATH}?r=0&g=0&b=0"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    return resp.status < 400
        except aiohttp.ClientError:
            return False
