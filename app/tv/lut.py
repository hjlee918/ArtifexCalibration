from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
import numpy as np


@dataclass
class LUT1D:
    """1D LUT: shape (3, N) — rows are R, G, B; values in [0, 1] float32.
    Convert to uint16 (scale * 65535) before passing to bscpylgtv.upload_1d_lut().
    """
    data: np.ndarray   # shape (3, N), dtype float32
    title: str = ""


@dataclass
class LUT3D:
    """3D LUT: shape (N, N, N, 3) — indexed as [R, G, B], output is RGB; values in [0, 1] float32.
    Convert to uint16 before passing to bscpylgtv.upload_3d_lut_bt709().
    .cube files iterate R fastest, then G, then B — parse_cube handles the transpose.
    """
    data: np.ndarray   # shape (N, N, N, 3), dtype float32
    size: int = 17
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    title: str = ""


def parse_cube(path: Path) -> LUT3D:
    """Parse an Adobe .cube 3D LUT file into a LUT3D with float32 [0,1] data."""
    path = Path(path)
    if path.suffix.lower() != ".cube":
        raise ValueError(f"Expected .cube file, got: {path.suffix}")

    title = ""
    size = None
    domain_min = (0.0, 0.0, 0.0)
    domain_max = (1.0, 1.0, 1.0)
    data_lines: list[str] = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("TITLE"):
                title = line.split(None, 1)[1].strip('"')
            elif line.startswith("LUT_3D_SIZE"):
                size = int(line.split()[1])
            elif line.startswith("DOMAIN_MIN"):
                parts = line.split()
                domain_min = (float(parts[1]), float(parts[2]), float(parts[3]))
            elif line.startswith("DOMAIN_MAX"):
                parts = line.split()
                domain_max = (float(parts[1]), float(parts[2]), float(parts[3]))
            else:
                data_lines.append(line)

    if size is None:
        raise ValueError(f"LUT_3D_SIZE not found in {path}")
    if len(data_lines) != size ** 3:
        raise ValueError(
            f"Expected {size**3} data lines, got {len(data_lines)} in {path}"
        )

    # .cube order: R varies fastest, then G, then B (outermost)
    # np.array shape after reshape: (B, G, R, 3)
    # Transpose to (R, G, B, 3) for intuitive data[r, g, b] indexing
    raw = np.array(
        [[float(v) for v in ln.split()] for ln in data_lines],
        dtype=np.float32,
    )
    data = raw.reshape(size, size, size, 3).transpose(2, 1, 0, 3)

    return LUT3D(data=data, size=size, domain_min=domain_min,
                 domain_max=domain_max, title=title)


def parse_cal(path: Path) -> LUT1D:
    """Parse an ArgyllCMS .cal 1D LUT file into a LUT1D with float32 [0,1] data."""
    path = Path(path)
    if path.suffix.lower() != ".cal":
        raise ValueError(f"Expected .cal file, got: {path.suffix}")

    title = ""
    in_data = False
    r_vals: list[float] = []
    g_vals: list[float] = []
    b_vals: list[float] = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DESCRIPTOR"):
                title = line.split(None, 1)[1].strip('"')
            elif line == "BEGIN_DATA":
                in_data = True
            elif line == "END_DATA":
                in_data = False
            elif in_data and line:
                parts = line.split()
                r_vals.append(float(parts[0]))
                g_vals.append(float(parts[1]))
                b_vals.append(float(parts[2]))

    data = np.array([r_vals, g_vals, b_vals], dtype=np.float32)
    return LUT1D(data=data, title=title)
