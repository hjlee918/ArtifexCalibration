# tests/unit/test_measurement_panel.py
import pytest
from unittest.mock import AsyncMock
from PyQt6.QtWidgets import QApplication, QPushButton, QComboBox, QLabel
from app.ui.measurement_panel import MeasurementPanel
from app.meter.device import MeterDevice, MeterType


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app):
    p = MeasurementPanel(on_run=AsyncMock(), on_upload_lut=AsyncMock())
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
