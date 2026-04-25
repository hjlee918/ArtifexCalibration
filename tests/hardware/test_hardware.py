# tests/hardware/test_hardware.py
import pytest
from app.tv.discovery import discover_tvs
from app.tv.connection import ConnectionManager
from app.tv.state import ChipGeneration

TV_IP = "192.168.1.101"  # Update to your C1/C2/C3+ IP before running


@pytest.mark.hardware
async def test_discover_finds_tv():
    tvs = await discover_tvs(timeout=5.0)
    ips = [tv.ip for tv in tvs]
    assert TV_IP in ips, f"Expected to find TV at {TV_IP}. Found: {ips}"


@pytest.mark.hardware
async def test_connect_and_detect_model():
    mgr = ConnectionManager(TV_IP)
    await mgr.connect()
    assert mgr.is_connected
    assert mgr.snapshot.chip_generation != ChipGeneration.UNKNOWN
    assert mgr.snapshot.webos_version != ""
    await mgr.disconnect()


@pytest.mark.hardware
async def test_firmware_check_runs():
    mgr = ConnectionManager(TV_IP)
    await mgr.connect()
    # firmware_warning may be True or False depending on TV firmware
    assert isinstance(mgr.firmware_warning, bool)
    await mgr.disconnect()
