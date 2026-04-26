# tests/unit/test_measurement_panel.py
import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication, QPushButton, QComboBox, QLabel
from app.ui.measurement_panel import MeasurementPanel
from app.meter.device import MeterDevice, MeterType


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app):
    p = MeasurementPanel(on_run=MagicMock(), on_upload_lut=MagicMock())
    yield p
    p.close()


def test_panel_creates(panel):
    assert panel is not None


def test_panel_has_run_button(panel):
    buttons = [b.text() for b in panel.findChildren(QPushButton)]
    assert any("measure" in t.lower() or "run" in t.lower() or "start" in t.lower() for t in buttons)


def test_panel_has_sequence_selector(panel):
    combos = panel.findChildren(QComboBox)
    assert len(combos) >= 1
    all_items = []
    for c in combos:
        for i in range(c.count()):
            all_items.append(c.itemText(i))
    assert any("SDR" in item or "sdr" in item.lower() for item in all_items)


def test_populate_meters_updates_combo(panel):
    devices = [
        MeterDevice(0, "i1 Display Pro", MeterType.COLORIMETER),
        MeterDevice(1, "i1 Pro 2", MeterType.SPECTROPHOTOMETER),
    ]
    panel.populate_meters(devices)
    combos = panel.findChildren(QComboBox)
    meter_items = []
    for c in combos:
        for i in range(c.count()):
            meter_items.append(c.itemText(i))
    assert any("i1" in item for item in meter_items)


def test_set_progress_zero_total(panel):
    panel.set_progress(0, 0)  # should not raise ZeroDivisionError
    assert panel._progress_bar.value() == 0


def test_set_running_disables_run_button(panel):
    panel.set_running(True)
    assert not panel._run_btn.isEnabled()
    assert "measur" in panel._run_btn.text().lower()
    panel.set_running(False)
    assert panel._run_btn.isEnabled()


def test_enable_upload_enables_button(panel):
    assert not panel._upload_btn.isEnabled()
    panel.enable_upload()
    assert panel._upload_btn.isEnabled()


def test_populate_meters_updates_meter_combo_directly(panel):
    devices = [
        MeterDevice(0, "i1 Display Pro", MeterType.COLORIMETER),
    ]
    panel.populate_meters(devices)
    items = [panel._meter_combo.itemText(i) for i in range(panel._meter_combo.count())]
    assert any("i1" in item for item in items)
