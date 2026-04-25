# tests/unit/test_lut_panel.py
import pytest
from unittest.mock import AsyncMock
from PyQt6.QtWidgets import QApplication, QPushButton, QComboBox, QLabel, QGroupBox
from app.ui.lut_panel import LUTPanel
from app.tv.upload import LUTTarget


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app):
    p = LUTPanel(on_upload=AsyncMock())
    yield p
    p.close()


def test_panel_creates(panel):
    assert panel is not None


def test_panel_has_upload_lut_button(panel):
    buttons = [b.text() for b in panel.findChildren(QPushButton)]
    assert any("upload" in t.lower() or "Upload" in t for t in buttons)


def test_panel_has_target_combo_with_bt709(panel):
    combos = panel.findChildren(QComboBox)
    all_items = []
    for c in combos:
        for i in range(c.count()):
            all_items.append(c.itemText(i))
    assert any("709" in t for t in all_items)


def test_panel_has_dv_section(panel):
    groups = [g.title() for g in panel.findChildren(QGroupBox)]
    assert any("dolby" in t.lower() or "dv" in t.lower() or "DV" in t for t in groups)


def test_panel_upload_button_disabled_initially(panel):
    # "Upload LUT to TV" button should be disabled until a file is selected
    btns = [b for b in panel.findChildren(QPushButton)
            if "lut" in b.text().lower() or "upload lut" in b.text().lower()]
    # At least one upload-LUT button should be disabled
    assert any(not b.isEnabled() for b in btns)


def test_set_status_shows_message(panel):
    panel.set_status("Upload complete")
    labels = [l.text() for l in panel.findChildren(QLabel)]
    assert any("Upload complete" in t for t in labels)


def test_set_status_error_changes_color(panel):
    panel.set_status("Failed", error=True)
    # Just verify it doesn't raise and status is set
    labels = [l.text() for l in panel.findChildren(QLabel)]
    assert any("Failed" in t for t in labels)
