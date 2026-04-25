import numpy as np
import pytest
from pathlib import Path
from app.tv.lut import LUT1D, LUT3D, parse_cube, parse_cal

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_cube_identity_17():
    lut = parse_cube(FIXTURES / "test_lut_17.cube")
    assert isinstance(lut, LUT3D)
    assert lut.size == 17
    assert lut.data.shape == (17, 17, 17, 3)
    # identity LUT: output at (8, 8, 8) should be (0.5, 0.5, 0.5)
    np.testing.assert_allclose(lut.data[8, 8, 8], [0.5, 0.5, 0.5], atol=1e-4)


def test_parse_cube_domain():
    lut = parse_cube(FIXTURES / "test_lut_17.cube")
    assert lut.domain_min == (0.0, 0.0, 0.0)
    assert lut.domain_max == (1.0, 1.0, 1.0)


def test_parse_cube_values_in_range():
    lut = parse_cube(FIXTURES / "test_lut_17.cube")
    assert lut.data.min() >= 0.0
    assert lut.data.max() <= 1.0


def test_parse_cube_axis_order():
    # .cube iterates R fastest, G middle, B slowest
    # After parse, data[r, g, b] should return (r/(N-1), g/(N-1), b/(N-1))
    lut = parse_cube(FIXTURES / "test_lut_17.cube")
    N = 16  # max index
    np.testing.assert_allclose(lut.data[0, 0, 0], [0.0, 0.0, 0.0], atol=1e-5)
    np.testing.assert_allclose(lut.data[N, 0, 0], [1.0, 0.0, 0.0], atol=1e-5)
    np.testing.assert_allclose(lut.data[0, N, 0], [0.0, 1.0, 0.0], atol=1e-5)
    np.testing.assert_allclose(lut.data[0, 0, N], [0.0, 0.0, 1.0], atol=1e-5)


def test_parse_cal_identity():
    lut = parse_cal(FIXTURES / "test_lut_1d.cal")
    assert isinstance(lut, LUT1D)
    assert lut.data.shape[0] == 3   # R, G, B rows
    assert lut.data.shape[1] == 3   # 3 entries in fixture


def test_parse_cal_values():
    lut = parse_cal(FIXTURES / "test_lut_1d.cal")
    # midpoint should be 0.5
    np.testing.assert_allclose(lut.data[:, 1], [0.5, 0.5, 0.5], atol=1e-6)
    # endpoint should be 1.0
    np.testing.assert_allclose(lut.data[:, 2], [1.0, 1.0, 1.0], atol=1e-6)


def test_parse_cube_wrong_extension_raises():
    with pytest.raises(ValueError, match="Expected .cube"):
        parse_cube(Path("file.txt"))


def test_parse_cal_wrong_extension_raises():
    with pytest.raises(ValueError, match="Expected .cal"):
        parse_cal(Path("file.txt"))
