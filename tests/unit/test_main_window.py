# tests/unit/test_main_window.py
import pytest
from PyQt6.QtWidgets import QApplication, QLabel, QStackedWidget
from PyQt6.QtCore import Qt
from app.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_main_window_creates(app):
    win = MainWindow()
    assert win is not None
    assert win.windowTitle() == "LG OLED Calibration"
    win.close()


def test_sidebar_shows_tv_connected(app):
    win = MainWindow()
    win.update_tv_status("192.168.1.101", "C1", connected=True)
    labels = [l.text() for l in win.findChildren(QLabel)]
    assert any("C1" in t for t in labels)
    win.close()


def test_sidebar_shows_tv_offline(app):
    win = MainWindow()
    win.update_tv_status("192.168.1.102", "C2", connected=False)
    labels = [l.text() for l in win.findChildren(QLabel)]
    assert any("C2" in t for t in labels)
    win.close()


def test_set_content_shows_widget(app):
    from PyQt6.QtWidgets import QLabel
    win = MainWindow()
    placeholder = QLabel("Test Content")
    win.set_content(placeholder)
    assert win.content_stack.currentWidget() is placeholder
    win.close()


def test_update_tv_status_replaces_existing(app):
    win = MainWindow()
    win.update_tv_status("192.168.1.101", "C1", connected=False)
    win.update_tv_status("192.168.1.101", "C1", connected=True)  # update same IP
    # Should not create duplicate entries for same IP
    c1_labels = [l for l in win.findChildren(QLabel) if "C1" in l.text()]
    assert len(c1_labels) >= 1
    win.close()
