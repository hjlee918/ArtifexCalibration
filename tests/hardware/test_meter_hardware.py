# tests/hardware/test_meter_hardware.py
import pytest
from app.meter.argyll import ArgyllReader, list_argyll_devices
from app.meter.device import XYZReading


@pytest.mark.hardware
def test_list_devices_finds_meter():
    """Requires: ArgyllCMS installed, at least one meter connected via USB."""
    devices = list_argyll_devices()
    assert len(devices) > 0, "No meters found — is a meter connected and ArgyllCMS installed?"


@pytest.mark.hardware
async def test_take_single_reading():
    """Requires: meter connected, pointing at a white surface or display."""
    reader = ArgyllReader(device_index=0, avg_count=1)
    reading = await reader.take_reading()
    assert isinstance(reading, XYZReading)
    assert reading.Y > 0, "Y value is 0 — is the meter pointing at a lit surface?"
