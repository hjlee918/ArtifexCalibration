"""Tests for meter device discovery and XYZ reading."""
from app.meter.device import MeterDevice, MeterType, XYZReading


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
