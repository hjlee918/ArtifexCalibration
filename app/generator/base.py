# app/generator/base.py
from abc import ABC, abstractmethod


class PatternGenerator(ABC):
    """Abstract interface for test pattern generators."""

    @abstractmethod
    async def start(self) -> None:
        """Activate the pattern generator."""

    @abstractmethod
    async def stop(self) -> None:
        """Deactivate the pattern generator."""

    @abstractmethod
    async def set_patch(self, r: int, g: int, b: int) -> None:
        """Display a patch with 8-bit RGB values (0–255)."""

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_):
        await self.stop()
