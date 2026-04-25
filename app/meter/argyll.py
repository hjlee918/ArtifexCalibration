"""ArgyllCMS subprocess wrapper for meter device discovery and XYZ reading."""
from __future__ import annotations
import asyncio
import re
import shutil
import subprocess
from app.meter.device import MeterDevice, MeterType, XYZReading


class ArgyllNotFoundError(RuntimeError):
    """Raised when ArgyllCMS (spotread) is not found in PATH."""
    pass


def _spotread_path() -> str:
    """Locate spotread executable in PATH.

    Raises:
        ArgyllNotFoundError: If spotread is not found.

    Returns:
        Path to spotread executable.
    """
    path = shutil.which("spotread")
    if path is None:
        raise ArgyllNotFoundError(
            "spotread not found. Install ArgyllCMS and ensure it is in PATH.\n"
            "macOS: brew install argyllcms"
        )
    return path


def list_argyll_devices() -> list[MeterDevice]:
    """Return connected measurement devices by running spotread with -? flag.

    Returns:
        List of MeterDevice objects (colorimeter or spectrophotometer).

    Raises:
        ArgyllNotFoundError: If spotread is not found.
    """
    spotread = _spotread_path()
    result = subprocess.run(
        [spotread, "-?"],
        capture_output=True,
        timeout=10,
    )
    output = result.stdout.decode(errors="ignore")
    devices: list[MeterDevice] = []
    for line in output.splitlines():
        m = re.match(r"\s*(\d+)\s*=\s*'(.+)'", line)
        if m:
            idx = int(m.group(1))
            name = m.group(2).strip()
            # Classify based on device name
            meter_type = (MeterType.SPECTROPHOTOMETER
                          if "Pro 2" in name or "spectro" in name.lower()
                          else MeterType.COLORIMETER)
            devices.append(MeterDevice(index=idx, name=name, meter_type=meter_type))
    return devices


class ArgyllReader:
    """Interface to spotread for taking colorimetric measurements."""

    def __init__(self, device_index: int = 0, avg_count: int = 3):
        """Initialize reader for a specific device.

        Args:
            device_index: Spotread device index (0 = first device).
            avg_count: Number of readings to average.
        """
        self.device_index = device_index
        self.avg_count = avg_count

    async def take_reading(self) -> XYZReading:
        """Take a single averaged XYZ reading asynchronously.

        Returns:
            XYZReading with CIE XYZ coordinates (cd/m² scale).

        Raises:
            RuntimeError: If spotread fails or CGATS parsing fails.
            ArgyllNotFoundError: If spotread is not found.
        """
        spotread = _spotread_path()
        cmd = [
            spotread,
            "-d", str(self.device_index),
            "-e", str(self.avg_count),
            "-O", "-",
        ]
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, timeout=30),
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"spotread failed (code {result.returncode}): "
                f"{result.stderr.decode(errors='ignore')}"
            )
        return _parse_cgats_xyz(result.stdout.decode(errors="ignore"))


def _parse_cgats_xyz(text: str) -> XYZReading:
    """Extract first XYZ triplet from CGATS output.

    Args:
        text: CGATS-formatted text from spotread.

    Returns:
        XYZReading with the first data row.

    Raises:
        ValueError: If no XYZ data found in CGATS output.
    """
    in_data = False
    for line in text.splitlines():
        line = line.strip()
        if line == "BEGIN_DATA":
            in_data = True
            continue
        if line == "END_DATA":
            break
        if in_data and line:
            parts = line.split()
            if len(parts) >= 4:
                return XYZReading(X=float(parts[1]), Y=float(parts[2]), Z=float(parts[3]))
    raise ValueError("No XYZ data found in CGATS output")
