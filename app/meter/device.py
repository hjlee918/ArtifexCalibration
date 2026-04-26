"""Device types and reading models for colorimeters and spectrophotometers."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class MeterType(Enum):
    """Measurement device type."""
    COLORIMETER = "colorimeter"
    SPECTROPHOTOMETER = "spectrophotometer"
    UNKNOWN = "unknown"


@dataclass
class MeterDevice:
    """A connected measurement device (colorimeter or spectrophotometer)."""
    index: int
    name: str
    meter_type: MeterType = MeterType.UNKNOWN


@dataclass
class XYZReading:
    """A single colorimetric reading in CIE XYZ (absolute, cd/m² scale)."""
    X: float
    Y: float
    Z: float

    @property
    def xyY(self) -> tuple[float, float, float]:
        """Convert to CIE xyY (chromaticity + luminance).

        Returns:
            (x, y, Y): where x, y are chromaticity coordinates and Y is luminance.
            Returns (0, 0, 0) for black (X=Y=Z=0).
        """
        total = self.X + self.Y + self.Z
        if total == 0:
            return (0.0, 0.0, 0.0)
        return (self.X / total, self.Y / total, self.Y)
