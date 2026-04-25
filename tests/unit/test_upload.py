# tests/unit/test_upload.py
import numpy as np
import pytest
from unittest.mock import AsyncMock
from app.tv.lut import LUT1D, LUT3D
from app.tv.upload import LUTUploader, LUTTarget


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.upload_1d_lut = AsyncMock(return_value=None)   # bscpylgtv returns None on success
    client.upload_3d_lut_bt709 = AsyncMock(return_value=None)
    client.upload_3d_lut_bt2020 = AsyncMock(return_value=None)
    client.set_3by3_gamut_data_bt709 = AsyncMock(return_value=None)
    client.set_3by3_gamut_data_bt2020 = AsyncMock(return_value=None)
    return client


@pytest.fixture
def uploader(mock_client):
    return LUTUploader(client=mock_client, pic_mode="expert1")


@pytest.fixture
def identity_1d():
    data = np.tile(np.linspace(0, 1, 1024, dtype=np.float32), (3, 1))
    return LUT1D(data=data)


@pytest.fixture
def identity_3d():
    size = 17
    data = np.zeros((size, size, size, 3), dtype=np.float32)
    for r in range(size):
        for g in range(size):
            for b in range(size):
                data[r, g, b] = [r / (size-1), g / (size-1), b / (size-1)]
    return LUT3D(data=data, size=size)


async def test_upload_1d_calls_client_with_uint16(uploader, mock_client, identity_1d):
    await uploader.upload_1d(identity_1d)
    mock_client.upload_1d_lut.assert_called_once()
    arg = mock_client.upload_1d_lut.call_args[0][0]
    assert arg.dtype == np.uint16
    assert arg.shape == (3, 1024)


async def test_upload_1d_scales_to_65535(uploader, mock_client, identity_1d):
    await uploader.upload_1d(identity_1d)
    arg = mock_client.upload_1d_lut.call_args[0][0]
    assert arg.max() == 65535   # identity LUT max should be 65535
    assert arg.min() == 0


async def test_upload_3d_bt709_calls_client_with_uint16(uploader, mock_client, identity_3d):
    await uploader.upload_3d(identity_3d, target=LUTTarget.BT709)
    mock_client.upload_3d_lut_bt709.assert_called_once()
    arg = mock_client.upload_3d_lut_bt709.call_args[0][0]
    assert arg.dtype == np.uint16
    assert arg.shape == (17, 17, 17, 3)


async def test_upload_3d_bt2020_calls_client(uploader, mock_client, identity_3d):
    await uploader.upload_3d(identity_3d, target=LUTTarget.BT2020)
    mock_client.upload_3d_lut_bt2020.assert_called_once()


async def test_upload_3d_wrong_target_raises(uploader, identity_3d):
    with pytest.raises(ValueError, match="Unknown LUTTarget"):
        await uploader.upload_3d(identity_3d, target="bad_target")


async def test_upload_1d_resamples_non_1024(uploader, mock_client):
    # LUT with only 3 points should be resampled to 1024
    data = np.array([[0, 0.5, 1], [0, 0.5, 1], [0, 0.5, 1]], dtype=np.float32)
    lut = LUT1D(data=data)
    await uploader.upload_1d(lut)
    arg = mock_client.upload_1d_lut.call_args[0][0]
    assert arg.shape == (3, 1024)
    assert arg.dtype == np.uint16


async def test_upload_file_path_1d(uploader, mock_client):
    # upload_file uses bscpylgtv's own from_file method directly
    from pathlib import Path
    import asyncio
    mock_client.upload_1d_lut_from_file = AsyncMock(return_value=None)
    await uploader.upload_file(Path("test.cal"))
    mock_client.upload_1d_lut_from_file.assert_called_once()


async def test_upload_file_path_3d_bt709(uploader, mock_client):
    from pathlib import Path
    mock_client.upload_3d_lut_bt709_from_file = AsyncMock(return_value=None)
    await uploader.upload_file(Path("test.cube"), target=LUTTarget.BT709)
    mock_client.upload_3d_lut_bt709_from_file.assert_called_once()


async def test_upload_gamut_matrix_bt709(uploader, mock_client):
    matrix = np.eye(3, dtype=np.float32)
    await uploader.upload_gamut_matrix(matrix, target=LUTTarget.BT709)
    mock_client.set_3by3_gamut_data_bt709.assert_called_once()
    arg = mock_client.set_3by3_gamut_data_bt709.call_args[0][0]
    assert arg.dtype == np.float32


async def test_upload_gamut_matrix_wrong_shape_raises(uploader):
    with pytest.raises(ValueError, match="must be"):
        await uploader.upload_gamut_matrix(np.eye(4), target=LUTTarget.BT709)


async def test_upload_file_cube_as_1d(uploader, mock_client):
    from pathlib import Path
    mock_client.upload_1d_lut_from_file = AsyncMock(return_value=None)
    await uploader.upload_file(Path("test.cube"), lut_type="1d")
    mock_client.upload_1d_lut_from_file.assert_called_once()
