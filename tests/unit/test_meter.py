"""Tests for meter device discovery and XYZ reading."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from app.meter.device import MeterDevice, MeterType, XYZReading
from app.meter.argyll import ArgyllReader, ArgyllNotFoundError, list_argyll_devices

FIXTURES = Path(__file__).parent.parent / "fixtures"

SPOTREAD_LIST_OUTPUT = b"""
spotread: Found 2 display measurement systems
 0 = 'X-Rite i1 Display Pro'
 1 = 'X-Rite i1 Pro 2'
"""


def test_meter_device_has_name_and_type():
    d = MeterDevice(index=0, name="i1 Display Pro", meter_type=MeterType.COLORIMETER)
    assert d.index == 0
    assert d.name == "i1 Display Pro"
    assert d.meter_type == MeterType.COLORIMETER


def test_meter_type_enum():
    assert MeterType.COLORIMETER != MeterType.SPECTROPHOTOMETER
    assert MeterType.UNKNOWN != MeterType.COLORIMETER


def test_xyz_reading_xyY():
    r = XYZReading(X=95.047, Y=100.0, Z=108.883)
    x, y, Y = r.xyY
    assert abs(x - 0.3127) < 0.001
    assert abs(y - 0.3290) < 0.001
    assert Y == 100.0


def test_xyz_reading_black_xyY():
    r = XYZReading(X=0.0, Y=0.0, Z=0.0)
    assert r.xyY == (0.0, 0.0, 0.0)


def test_list_argyll_devices_parses_output():
    with patch("app.meter.argyll.shutil.which", return_value="/usr/bin/spotread"):
        with patch("app.meter.argyll.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=SPOTREAD_LIST_OUTPUT, returncode=1)
            devices = list_argyll_devices()
    assert len(devices) == 2
    assert devices[0].index == 0
    assert "i1 Display Pro" in devices[0].name
    assert devices[1].index == 1
    assert "i1 Pro 2" in devices[1].name


def test_list_argyll_devices_classifies_spectro():
    with patch("app.meter.argyll.shutil.which", return_value="/usr/bin/spotread"):
        with patch("app.meter.argyll.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=SPOTREAD_LIST_OUTPUT, returncode=1)
            devices = list_argyll_devices()
    assert devices[0].meter_type == MeterType.COLORIMETER
    assert devices[1].meter_type == MeterType.SPECTROPHOTOMETER


def test_list_argyll_devices_no_spotread_raises():
    with patch("app.meter.argyll.shutil.which", return_value=None):
        with pytest.raises(ArgyllNotFoundError):
            list_argyll_devices()


async def test_take_reading_parses_cgats():
    reader = ArgyllReader(device_index=0)
    cgats_text = (FIXTURES / "sample_cgats.txt").read_text()
    with patch("app.meter.argyll.shutil.which", return_value="/usr/bin/spotread"):
        with patch("app.meter.argyll.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=cgats_text.encode(), returncode=0)
            reading = await reader.take_reading()
    assert isinstance(reading, XYZReading)
    assert abs(reading.X - 95.047) < 0.01
    assert abs(reading.Y - 100.000) < 0.01
    assert abs(reading.Z - 108.883) < 0.01


async def test_take_reading_subprocess_failure_raises():
    reader = ArgyllReader(device_index=0)
    with patch("app.meter.argyll.shutil.which", return_value="/usr/bin/spotread"):
        with patch("app.meter.argyll.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"", returncode=2)
            with pytest.raises(RuntimeError, match="spotread failed"):
                await reader.take_reading()
