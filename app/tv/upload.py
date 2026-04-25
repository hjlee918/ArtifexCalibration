# app/tv/upload.py
# NOTE: bscpylgtv raises PyLGTVCmdException on failure — it does NOT return
# {"returnValue": False}. No _check_result guard needed for production paths.
# The mock_client in tests returns None on success (matching real bscpylgtv behavior).
from __future__ import annotations
from enum import Enum
from pathlib import Path
import numpy as np
from bscpylgtv import WebOsClient
from app.tv.lut import LUT1D, LUT3D

_UINT16_MAX = 65535


class LUTTarget(str, Enum):
    BT709 = "bt709"
    BT2020 = "bt2020"


class LUTUploader:
    def __init__(self, client: WebOsClient, pic_mode: str = "expert1"):
        self._client = client
        self.pic_mode = pic_mode

    async def upload_1d(self, lut: LUT1D) -> None:
        """Upload 1D LUT from in-memory LUT1D. Converts float32→uint16 (3, 1024)."""
        data = _to_uint16_1d(lut.data)
        await self._client.upload_1d_lut(data)

    async def upload_3d(self, lut: LUT3D, target: LUTTarget) -> None:
        """Upload 3D LUT from in-memory LUT3D. Converts float32→uint16 (N,N,N,3)."""
        data = _to_uint16_3d(lut.data)
        if target == LUTTarget.BT709:
            await self._client.upload_3d_lut_bt709(data)
        elif target == LUTTarget.BT2020:
            await self._client.upload_3d_lut_bt2020(data)
        else:
            raise ValueError(f"Unknown LUTTarget: {target!r}")

    async def upload_file(self, path: Path,
                          target: LUTTarget = LUTTarget.BT709) -> None:
        """Upload a LUT file using bscpylgtv's own file parsers (no in-memory conversion).
        Supported: .cal, .cube, .1dlut for 1D; .cube, .3dlut for 3D.
        For .cal files, always uploads as 1D LUT.
        """
        path = Path(path)
        ext = path.suffix.lower()
        if ext in (".cal", ".1dlut"):
            await self._client.upload_1d_lut_from_file(str(path))
        elif ext == ".cube":
            if target == LUTTarget.BT709:
                await self._client.upload_3d_lut_bt709_from_file(str(path))
            else:
                await self._client.upload_3d_lut_bt2020_from_file(str(path))
        else:
            raise ValueError(f"Unsupported file extension for LUT upload: {ext}")

    async def upload_gamut_matrix(self, matrix: np.ndarray,
                                   target: LUTTarget = LUTTarget.BT709) -> None:
        """Upload a 3×3 gamut matrix. Uses bscpylgtv set_3by3_gamut_data_bt709/bt2020."""
        if matrix.shape != (3, 3):
            raise ValueError(f"Gamut matrix must be (3, 3), got {matrix.shape}")
        data = matrix.astype(np.float64)  # bscpylgtv uses float64 for gamut matrix
        if target == LUTTarget.BT709:
            await self._client.set_3by3_gamut_data_bt709(data)
        else:
            await self._client.set_3by3_gamut_data_bt2020(data)


def _to_uint16_1d(data: np.ndarray) -> np.ndarray:
    """Resample to 1024 points and convert float32 [0,1] → uint16 [0,65535]."""
    if data.shape[1] != 1024:
        x_in = np.linspace(0, 1, data.shape[1])
        x_out = np.linspace(0, 1, 1024)
        resampled = np.zeros((3, 1024), dtype=np.float32)
        for ch in range(3):
            resampled[ch] = np.interp(x_out, x_in, data[ch])
        data = resampled
    return np.round(data * _UINT16_MAX).astype(np.uint16)


def _to_uint16_3d(data: np.ndarray) -> np.ndarray:
    """Convert float32 [0,1] 3D LUT → uint16 [0,65535]."""
    return np.round(data * _UINT16_MAX).astype(np.uint16)
