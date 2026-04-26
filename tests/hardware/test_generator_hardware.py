# tests/hardware/test_generator_hardware.py
import pytest
from app.generator.itpg import iTPGGenerator
from app.generator.pgenerator import PGeneratorClient
from app.tv.connection import ConnectionManager

TV_IP = "192.168.1.101"    # Update before running
PGEN_IP = "192.168.1.200"  # Update before running


@pytest.fixture
async def connected_mgr():
    mgr = ConnectionManager(TV_IP)
    await mgr.connect()
    yield mgr
    await mgr.disconnect()


@pytest.mark.hardware
async def test_itpg_displays_white_patch(connected_mgr):
    gen = iTPGGenerator(client=connected_mgr.client)
    async with gen:
        await gen.set_patch(255, 255, 255)


@pytest.mark.hardware
async def test_itpg_displays_red_patch(connected_mgr):
    gen = iTPGGenerator(client=connected_mgr.client)
    async with gen:
        await gen.set_patch(255, 0, 0)


@pytest.mark.hardware
async def test_pgenerator_probe():
    gen = PGeneratorClient(host=PGEN_IP)
    result = await gen.probe()
    assert result is True, f"PGenerator not reachable at {PGEN_IP}:8080"


@pytest.mark.hardware
async def test_pgenerator_displays_white():
    gen = PGeneratorClient(host=PGEN_IP)
    async with gen:
        await gen.set_patch(255, 255, 255)
