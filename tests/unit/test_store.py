# tests/unit/test_store.py
import json
import pytest
from pathlib import Path
from app.measurement.store import save_cgats, load_cgats, save_json, load_json
from app.measurement.session import PatchResult
from app.measurement.patches import Patch
from app.meter.device import XYZReading


@pytest.fixture
def sample_results():
    return [
        PatchResult(patch=Patch(0, 0, 0, "Black"), reading=XYZReading(0.0, 0.0, 0.0)),
        PatchResult(patch=Patch(255, 255, 255, "White"), reading=XYZReading(95.0, 100.0, 108.9)),
    ]


def test_save_and_load_cgats(tmp_path, sample_results):
    path = tmp_path / "results.cgats"
    save_cgats(sample_results, path)
    assert path.exists()
    loaded = load_cgats(path)
    assert len(loaded) == 2
    assert abs(loaded[1].reading.Y - 100.0) < 0.01
    assert loaded[1].patch.label == "White"


def test_cgats_format_has_required_headers(tmp_path, sample_results):
    path = tmp_path / "results.cgats"
    save_cgats(sample_results, path)
    text = path.read_text()
    assert "CGATS" in text
    assert "XYZ_X" in text
    assert "BEGIN_DATA" in text
    assert "END_DATA" in text


def test_save_and_load_json(tmp_path, sample_results):
    path = tmp_path / "results.json"
    save_json(sample_results, path)
    assert path.exists()
    loaded = load_json(path)
    assert len(loaded) == 2
    assert loaded[0].patch.label == "Black"
    assert abs(loaded[1].reading.X - 95.0) < 0.01


def test_json_round_trip_preserves_rgb(tmp_path, sample_results):
    path = tmp_path / "results.json"
    save_json(sample_results, path)
    loaded = load_json(path)
    assert loaded[1].patch.r == 255
    assert loaded[1].patch.g == 255
    assert loaded[1].patch.b == 255


def test_cgats_round_trip_xyz(tmp_path, sample_results):
    path = tmp_path / "results.cgats"
    save_cgats(sample_results, path)
    loaded = load_cgats(path)
    assert abs(loaded[1].reading.Z - 108.9) < 0.01


def test_cgats_round_trips_multi_word_label(tmp_path):
    from app.measurement.patches import build_sdr_full
    seq = build_sdr_full()
    results = [
        PatchResult(patch=p, reading=XYZReading(X=10.0, Y=10.0, Z=10.0))
        for p in seq.patches
    ]
    path = tmp_path / "full.cgats"
    save_cgats(results, path)
    loaded = load_cgats(path)
    assert len(loaded) == 30
    # Verify labels with spaces round-trip correctly
    assert loaded[21].patch.label == "Red 100%"
    assert loaded[24].patch.label == "Cyan 100%"
    assert loaded[27].patch.label == "Red 50%"
