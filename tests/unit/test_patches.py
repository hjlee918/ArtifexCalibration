# tests/unit/test_patches.py
from app.measurement.patches import (
    Patch, PatchSequence,
    SDR_GRAYSCALE_21, SDR_PRIMARIES, SDR_SECONDARIES, HDR10_GRAYSCALE,
    build_sdr_full, build_hdr10_full,
)

def test_patch_has_rgb():
    p = Patch(r=128, g=0, b=0, label="50% Red")
    assert p.r == 128 and p.g == 0 and p.b == 0
    assert p.label == "50% Red"

def test_sdr_grayscale_21_has_21_patches():
    assert len(SDR_GRAYSCALE_21) == 21
    assert SDR_GRAYSCALE_21[0].r == 0
    assert SDR_GRAYSCALE_21[-1].r == 255

def test_sdr_grayscale_steps():
    # 5% steps: index 1 = 5% = round(0.05*255) = 13
    assert SDR_GRAYSCALE_21[1].r == 13
    assert SDR_GRAYSCALE_21[1].g == 13
    assert SDR_GRAYSCALE_21[1].b == 13

def test_sdr_primaries_has_6_patches():
    assert len(SDR_PRIMARIES) == 6

def test_sdr_secondaries_has_3_patches():
    assert len(SDR_SECONDARIES) == 3

def test_build_sdr_full_has_30_patches():
    seq = build_sdr_full()
    assert isinstance(seq, PatchSequence)
    assert len(seq.patches) == 30  # 21 + 6 + 3

def test_build_hdr10_full_has_primaries():
    seq = build_hdr10_full()
    assert len(seq.patches) == len(HDR10_GRAYSCALE) + 6

def test_hdr10_grayscale_patches_labeled():
    for p in HDR10_GRAYSCALE:
        assert p.label != ""
        assert "nit" in p.label.lower()

def test_patch_sequence_iterable():
    seq = build_sdr_full()
    patches = list(seq)
    assert len(patches) == 30

def test_patch_sequence_len():
    seq = build_sdr_full()
    assert len(seq) == 30
