# app/lut_gen/tone_curve.py
from __future__ import annotations
import numpy as np
from app.measurement.session import PatchResult
from app.tv.lut import LUT1D


def generate_1d_lut_from_grayscale(
    results: list[PatchResult],
    target_gamma: float = 2.4,
    lut_size: int = 1024,
) -> LUT1D:
    """Generate a 1D correction LUT from grayscale patch measurements.

    Computes the per-code correction ratio needed to bring the display's
    measured response to the target gamma curve, then interpolates to
    lut_size output points.
    """
    stimulus = np.array([r.patch.r / 255.0 for r in results])
    y_vals = np.array([r.reading.Y for r in results])

    white_Y = float(np.max(y_vals))
    if white_Y == 0:
        raise ValueError("White point Y is zero — check measurement data")
    y_norm = y_vals / white_Y

    eps = 1e-6
    y_target = np.where(stimulus > 0, stimulus ** target_gamma, 0.0)
    y_norm_safe = np.where(y_norm > eps, y_norm, eps)
    correction_ratio = np.where(y_target > eps, y_target / y_norm_safe, 1.0)

    x_lut = np.linspace(0, 1, lut_size)
    correction_interp = np.interp(x_lut, stimulus, correction_ratio)
    lut_out = np.clip(x_lut * correction_interp, 0, 1).astype(np.float32)

    data = np.stack([lut_out, lut_out, lut_out], axis=0)
    return LUT1D(data=data)
