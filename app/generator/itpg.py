# app/generator/itpg.py
from __future__ import annotations
from bscpylgtv import WebOsClient
from app.generator.base import PatternGenerator

_10BIT_MAX = 1023
_8BIT_MAX = 255


def _to_10bit(v: int) -> int:
    return round(v / _8BIT_MAX * _10BIT_MAX)


class iTPGGenerator(PatternGenerator):
    """LG internal Test Pattern Generator via bscpylgtv SSAP."""

    def __init__(self, client: WebOsClient,
                 win_h: int = 100, win_v: int = 100,
                 patch_h: int = 50, patch_v: int = 50):
        self._client = client
        self._win_h = win_h
        self._win_v = win_v
        self._patch_h = patch_h
        self._patch_v = patch_v

    async def start(self) -> None:
        await self._client.start_itpg()
        await self._client.set_itpg_patch_window(
            self._win_h, self._win_v, self._patch_h, self._patch_v
        )

    async def stop(self) -> None:
        await self._client.stop_itpg()

    async def set_patch(self, r: int, g: int, b: int) -> None:
        await self._client.set_itpg_patch_color(
            _to_10bit(r), _to_10bit(g), _to_10bit(b)
        )
