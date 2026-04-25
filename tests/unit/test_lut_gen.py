# tests/unit/test_lut_gen.py
import numpy as np
import pytest
from app.measurement.session import PatchResult
from app.measurement.patches import Patch, SDR_GRAYSCALE_21
from app.meter.device import XYZReading
from app.lut_gen.tone_curve import generate_1d_lut_from_grayscale
from app.lut_gen.gamut import generate_3d_lut_from_measurements
from app.tv.lut import LUT1D, LUT3D


def _linear_gray_results() -> list[PatchResult]:
    """Synthetic: Y rises linearly with code value."""
    results = []
    for patch in SDR_GRAYSCALE_21:
        stim = patch.r / 255
        Y = stim * 100.0
        results.append(PatchResult(patch=patch, reading=XYZReading(X=Y*0.95, Y=Y, Z=Y*1.09)))
    return results


def _gamma24_gray_results() -> list[PatchResult]:
    """Synthetic: perfect gamma 2.4 display."""
    results = []
    for patch in SDR_GRAYSCALE_21:
        stim = patch.r / 255
        Y = (stim ** 2.4) * 100.0 if stim > 0 else 0.0
        results.append(PatchResult(patch=patch, reading=XYZReading(X=Y*0.95, Y=Y, Z=Y*1.09)))
    return results


def test_generate_1d_lut_returns_lut1d():
    lut = generate_1d_lut_from_grayscale(_linear_gray_results(), target_gamma=2.4)
    assert isinstance(lut, LUT1D)
    assert lut.data.shape == (3, 1024)
    assert lut.data.dtype == np.float32


def test_generate_1d_lut_output_in_range():
    lut = generate_1d_lut_from_grayscale(_linear_gray_results(), target_gamma=2.4)
    assert lut.data.min() >= 0.0
    assert lut.data.max() <= 1.0


def test_generate_1d_lut_symmetric_channels():
    lut = generate_1d_lut_from_grayscale(_linear_gray_results(), target_gamma=2.4)
    # R, G, B channels should be identical for grayscale-only measurements
    np.testing.assert_array_equal(lut.data[0], lut.data[1])
    np.testing.assert_array_equal(lut.data[1], lut.data[2])


def test_generate_1d_lut_identity_for_perfect_gamma24():
    lut = generate_1d_lut_from_grayscale(_gamma24_gray_results(), target_gamma=2.4)
    # Perfect display → near-identity LUT; midpoint should be close to 0.5
    midpoint = lut.data[0, 512]
    assert 0.4 < midpoint < 0.6


def test_generate_1d_lut_zero_white_raises():
    results = [PatchResult(patch=Patch(0,0,0,""), reading=XYZReading(0,0,0))]
    with pytest.raises(ValueError, match="White point"):
        generate_1d_lut_from_grayscale(results)


def test_generate_3d_lut_returns_lut3d():
    from app.measurement.patches import build_sdr_full
    results = []
    for patch in build_sdr_full():
        X = patch.r / 255 * 95.047
        Y = patch.g / 255 * 100.0
        Z = patch.b / 255 * 108.883
        results.append(PatchResult(patch=patch, reading=XYZReading(X=X, Y=Y, Z=Z)))
    lut = generate_3d_lut_from_measurements(results, lut_size=17)
    assert isinstance(lut, LUT3D)
    assert lut.size == 17
    assert lut.data.shape == (17, 17, 17, 3)
    assert lut.data.dtype == np.float32
    assert lut.data.min() >= 0.0
    assert lut.data.max() <= 1.0


def test_generate_1d_lut_is_monotonic():
    lut = generate_1d_lut_from_grayscale(_linear_gray_results(), target_gamma=2.4)
    # Non-monotonic 1D LUT causes color inversion artifacts on TV
    diffs = np.diff(lut.data[0])
    assert np.all(diffs >= 0), f"LUT has {(diffs < 0).sum()} non-monotonic steps"


def test_generate_3d_lut_identity_display_near_identity():
    """For a near-perfect display, the 3D LUT should be close to identity."""
    from app.measurement.patches import build_sdr_full
    import colour
    cs = colour.RGB_COLOURSPACES["ITU-R BT.709"]
    white_xyz = np.array([95.047, 100.0, 108.883])

    results = []
    for patch in build_sdr_full():
        stim = np.array([patch.r, patch.g, patch.b]) / 255.0
        # Perfect display: stimulus → XYZ via inverse BT.709 matrix
        xyz = cs.matrix_RGB_to_XYZ @ stim * 100.0
        results.append(PatchResult(
            patch=patch,
            reading=XYZReading(X=xyz[0], Y=xyz[1], Z=xyz[2])
        ))

    lut = generate_3d_lut_from_measurements(results, lut_size=9)
    # For a perfect display the 3D LUT correction should be near-zero everywhere
    # Check center of the LUT is close to (0.5, 0.5, 0.5)
    center = lut.data[4, 4, 4]
    assert np.allclose(center, [0.5, 0.5, 0.5], atol=0.05), f"Center: {center}"
