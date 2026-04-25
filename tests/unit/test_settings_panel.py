# tests/unit/test_settings_panel.py
import pytest
from PyQt6.QtWidgets import QApplication, QTabWidget, QSlider, QComboBox
from app.ui.settings_panel import SettingsPanel
from app.tv.state import TVSettingsSnapshot, ChipGeneration


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app):
    snap = TVSettingsSnapshot(
        oled_light=70,
        contrast=85,
        gamma="bt1886",
        chip_generation=ChipGeneration.ALPHA9_GEN4,
    )
    p = SettingsPanel(snapshot=snap, on_write=lambda coro: None)
    yield p
    p.close()


def test_panel_has_five_tabs(panel):
    tabs = panel.findChildren(QTabWidget)
    assert len(tabs) == 1
    assert tabs[0].count() == 5


def test_oled_light_slider_reflects_snapshot(panel):
    sliders = panel.findChildren(QSlider)
    oled_slider = next((s for s in sliders if s.objectName() == "oled_light"), None)
    assert oled_slider is not None
    assert oled_slider.value() == 70


def test_gamma_combobox_reflects_snapshot(panel):
    combos = panel.findChildren(QComboBox)
    gamma_combo = next((c for c in combos if c.findText("BT.1886") >= 0), None)
    assert gamma_combo is not None
    assert "1886" in gamma_combo.currentText().upper() or "BT.1886" in gamma_combo.currentText()


def test_panel_calls_on_write_when_slider_changes(app):
    wrote = []
    snap = TVSettingsSnapshot(oled_light=50)
    panel = SettingsPanel(snapshot=snap, on_write=lambda coro: wrote.append(coro))
    sliders = panel.findChildren(QSlider)
    oled_slider = next((s for s in sliders if s.objectName() == "oled_light"), None)
    if oled_slider:
        oled_slider.setValue(80)
        assert len(wrote) > 0
    panel.close()


def test_all_five_tab_names(panel):
    tabs = panel.findChildren(QTabWidget)[0]
    tab_texts = [tabs.tabText(i) for i in range(tabs.count())]
    assert any("Picture" in t for t in tab_texts)
    assert any("White" in t or "WB" in t for t in tab_texts)
    assert any("Gamma" in t or "Color Space" in t for t in tab_texts)
    assert any("Color" in t or "CMS" in t for t in tab_texts)
    assert any("HDR" in t or "Dynamic" in t for t in tab_texts)
