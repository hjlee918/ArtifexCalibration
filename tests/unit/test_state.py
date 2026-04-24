# tests/unit/test_state.py
from app.tv.state import TVSettingsSnapshot, ChipGeneration


def test_snapshot_has_defaults():
    snap = TVSettingsSnapshot()
    assert snap.oled_light == 50
    assert snap.contrast == 85
    assert snap.brightness == 50
    assert snap.pic_mode == "expert1"
    assert snap.chip_generation == ChipGeneration.UNKNOWN


def test_snapshot_update():
    snap = TVSettingsSnapshot()
    snap.oled_light = 70
    assert snap.oled_light == 70


def test_snapshot_wb_20pt_has_20_entries():
    snap = TVSettingsSnapshot()
    assert len(snap.wb_20pt_red) == 20
    assert len(snap.wb_20pt_green) == 20
    assert len(snap.wb_20pt_blue) == 20


def test_snapshot_cms_colors():
    snap = TVSettingsSnapshot()
    for color in ("red", "green", "blue", "cyan", "magenta", "yellow"):
        assert hasattr(snap, f"cms_{color}_hue")
        assert hasattr(snap, f"cms_{color}_saturation")
        assert hasattr(snap, f"cms_{color}_luminance")
        assert getattr(snap, f"cms_{color}_hue") == 0
        assert getattr(snap, f"cms_{color}_saturation") == 0
        assert getattr(snap, f"cms_{color}_luminance") == 0


def test_wb_20pt_lists_are_independent():
    a = TVSettingsSnapshot()
    b = TVSettingsSnapshot()
    a.wb_20pt_red[0] = 99
    assert b.wb_20pt_red[0] == 0


def test_calibration_safe_defaults():
    snap = TVSettingsSnapshot()
    assert snap.local_dimming == "off"
    assert snap.hdr_tone_mapping is False
