# tests/hardware/test_lut_hardware.py
import pytest
import numpy as np
from pathlib import Path
from app.tv.connection import ConnectionManager
from app.tv.upload import LUTUploader, LUTTarget
from app.tv.lut import LUT1D, LUT3D, parse_cube

TV_IP = "192.168.1.101"  # Update before running
FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def connected_mgr():
    mgr = ConnectionManager(TV_IP)
    await mgr.connect()
    yield mgr
    await mgr.disconnect()


@pytest.mark.hardware
async def test_upload_identity_1d_lut(connected_mgr):
    """Upload an identity 1D LUT — no-op visually but confirms upload API works."""
    data = np.tile(np.linspace(0, 1, 1024, dtype=np.float32), (3, 1))
    lut = LUT1D(data=data)
    uploader = LUTUploader(client=connected_mgr.client, pic_mode="expert1")
    await uploader.upload_1d(lut)


@pytest.mark.hardware
async def test_upload_identity_3d_lut_bt709(connected_mgr):
    """Upload an identity 3D LUT to BT.709 slot — no-op visually."""
    size = 17
    data = np.zeros((size, size, size, 3), dtype=np.float32)
    for r in range(size):
        for g in range(size):
            for b in range(size):
                data[r, g, b] = [r / (size-1), g / (size-1), b / (size-1)]
    lut = LUT3D(data=data, size=size)
    uploader = LUTUploader(client=connected_mgr.client, pic_mode="expert1")
    await uploader.upload_3d(lut, target=LUTTarget.BT709)


@pytest.mark.hardware
async def test_upload_cube_file_from_disk(connected_mgr):
    """Parse the identity .cube fixture and upload via file path."""
    uploader = LUTUploader(client=connected_mgr.client, pic_mode="expert1")
    await uploader.upload_file(FIXTURES / "test_lut_17.cube", target=LUTTarget.BT709)


@pytest.mark.hardware
async def test_upload_identity_gamut_matrix(connected_mgr):
    """Upload identity 3x3 matrix — no-op visually."""
    matrix = np.eye(3, dtype=np.float32)
    uploader = LUTUploader(client=connected_mgr.client, pic_mode="expert1")
    await uploader.upload_gamut_matrix(matrix, target=LUTTarget.BT709)
