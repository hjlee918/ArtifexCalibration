# app/lut_gen/gamut.py
# NOTE: This is a first-order approximation suitable for display calibration
# correction. For professional-grade results use DisplayCAL or LightSpace CMS
# with the CGATS measurement data as input.
from __future__ import annotations
import numpy as np
from app.measurement.session import PatchResult
from app.tv.lut import LUT3D

try:
    import colour
    _COLOUR_AVAILABLE = True
except ImportError:
    _COLOUR_AVAILABLE = False


def generate_3d_lut_from_measurements(
    results: list[PatchResult],
    lut_size: int = 17,
    target_colorspace: str = "ITU-R BT.709",
) -> LUT3D:
    """Generate a 3D correction LUT from a full patch set via RBF interpolation.

    Requires at least 30 measurements (grayscale + primaries + secondaries).
    """
    from scipy.interpolate import RBFInterpolator

    if not _COLOUR_AVAILABLE:
        raise ImportError("colour-science required: pip install colour-science")

    cs = colour.RGB_COLOURSPACES[target_colorspace]
    xyz_to_rgb = cs.matrix_XYZ_to_RGB

    white_Y = max(r.reading.Y for r in results)
    if white_Y == 0:
        raise ValueError("White point Y is zero")

    known_in = []
    known_correction = []
    for result in results:
        stim = np.array([result.patch.r, result.patch.g, result.patch.b]) / 255.0
        # colour's BT.709 matrix expects XYZ normalized so D65 white = [0.95047, 1.0, 1.08883]
        xyz = np.array([result.reading.X, result.reading.Y, result.reading.Z]) / white_Y
        measured_rgb = np.clip(xyz_to_rgb @ xyz, 0, 1)
        known_in.append(stim)
        known_correction.append(stim - measured_rgb)

    known_in = np.array(known_in)
    known_correction = np.array(known_correction)

    rbf = RBFInterpolator(known_in, known_correction, kernel="thin_plate_spline")

    grid_1d = np.linspace(0, 1, lut_size)
    R, G, B = np.meshgrid(grid_1d, grid_1d, grid_1d, indexing="ij")
    grid_pts = np.stack([R.ravel(), G.ravel(), B.ravel()], axis=1)

    corrections = rbf(grid_pts)
    corrected = np.clip(grid_pts + corrections, 0, 1)
    data = corrected.reshape(lut_size, lut_size, lut_size, 3).astype(np.float32)

    return LUT3D(data=data, size=lut_size)
