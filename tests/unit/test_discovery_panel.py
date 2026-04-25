# tests/unit/test_discovery_panel.py
import pytest
from unittest.mock import AsyncMock
from PyQt6.QtWidgets import QApplication, QListWidget, QLabel, QLineEdit
from app.ui.discovery_panel import DiscoveryPanel
from app.tv.discovery import DiscoveredTV


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_panel_shows_found_tvs(app):
    panel = DiscoveryPanel(on_connect=AsyncMock())
    tvs = [DiscoveredTV("192.168.1.101", "C1 OLED"), DiscoveredTV("192.168.1.102", "C2 OLED")]
    panel.show_discovered(tvs)
    list_widgets = panel.findChildren(QListWidget)
    assert any(lw.count() == 2 for lw in list_widgets)
    panel.close()


def test_panel_shows_no_tvs_message(app):
    panel = DiscoveryPanel(on_connect=AsyncMock())
    panel.show_discovered([])
    labels = [l.text() for l in panel.findChildren(QLabel)]
    assert any("No TVs" in t or "not found" in t.lower() for t in labels)
    panel.close()


def test_panel_has_manual_ip_input(app):
    panel = DiscoveryPanel(on_connect=AsyncMock())
    inputs = panel.findChildren(QLineEdit)
    assert len(inputs) >= 1
    panel.close()


def test_set_scanning_disables_button(app):
    panel = DiscoveryPanel(on_connect=AsyncMock())
    panel.set_scanning(True)
    from PyQt6.QtWidgets import QPushButton
    scan_btns = [b for b in panel.findChildren(QPushButton) if "Scan" in b.text() or "Scanning" in b.text()]
    assert all(not b.isEnabled() for b in scan_btns)
    panel.close()


def test_tv_selected_signal_emitted_on_scan(app):
    panel = DiscoveryPanel(on_connect=AsyncMock())
    signals = []
    panel.tv_selected.connect(lambda ip, name: signals.append((ip, name)))
    panel._on_scan_clicked()
    assert signals == [("__scan__", "")]
    panel.close()
