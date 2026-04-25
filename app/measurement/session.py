# app/measurement/session.py
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Callable, Optional
from app.generator.base import PatternGenerator
from app.meter.device import XYZReading
from app.measurement.patches import Patch, PatchSequence

_SETTLE_SECONDS = 0.5


@dataclass
class PatchResult:
    patch: Patch
    reading: XYZReading


class MeasurementSession:
    def __init__(
        self,
        generator: PatternGenerator,
        reader,
        sequence: PatchSequence,
        settle_time: float = _SETTLE_SECONDS,
        on_progress: Optional[Callable[[int, int, PatchResult], None]] = None,
    ):
        self._generator = generator
        self._reader = reader
        self._sequence = sequence
        self._settle_time = settle_time
        self._on_progress = on_progress

    async def run(self) -> list[PatchResult]:
        results: list[PatchResult] = []
        total = len(self._sequence)
        await self._generator.start()
        try:
            for i, patch in enumerate(self._sequence, start=1):
                await self._generator.set_patch(patch.r, patch.g, patch.b)
                if self._settle_time > 0:
                    await asyncio.sleep(self._settle_time)
                reading = await self._reader.take_reading()
                result = PatchResult(patch=patch, reading=reading)
                results.append(result)
                if self._on_progress:
                    self._on_progress(i, total, result)
        finally:
            await self._generator.stop()
        return results
