# app/ui/discovery_panel.py
from typing import Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.tv.discovery import DiscoveredTV


class DiscoveryPanel(QWidget):
    tv_selected = pyqtSignal(str, str)  # ip, name

    def __init__(self, on_connect: Callable, parent=None):
        super().__init__(parent)
        self._on_connect = on_connect
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Connect to TV")
        title.setStyleSheet("color: #fff; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        scan_row = QHBoxLayout()
        self._scan_btn = QPushButton("Scan Network")
        self._scan_btn.setStyleSheet(
            "background: #4fc3f7; color: #000; padding: 8px 16px; border-radius: 4px; font-weight: bold;"
        )
        self._scan_btn.clicked.connect(self._on_scan_clicked)
        scan_row.addWidget(self._scan_btn)
        scan_row.addStretch()
        layout.addLayout(scan_row)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(self._status_label)

        self._tv_list = QListWidget()
        self._tv_list.setStyleSheet(
            "background: #1a1a2e; color: #ccc; border: 1px solid #333; border-radius: 4px;"
        )
        self._tv_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._tv_list)

        manual_row = QHBoxLayout()
        manual_label = QLabel("Manual IP:")
        manual_label.setStyleSheet("color: #aaa; font-size: 12px;")
        self._ip_input = QLineEdit()
        self._ip_input.setPlaceholderText("192.168.1.xxx")
        self._ip_input.setStyleSheet(
            "background: #1a1a2e; color: #fff; border: 1px solid #333; padding: 4px; border-radius: 4px;"
        )
        connect_btn = QPushButton("Connect")
        connect_btn.setStyleSheet(
            "background: #2a2a3e; color: #aaa; padding: 4px 12px; border-radius: 4px;"
        )
        connect_btn.clicked.connect(self._on_manual_connect)
        manual_row.addWidget(manual_label)
        manual_row.addWidget(self._ip_input, 1)
        manual_row.addWidget(connect_btn)
        layout.addLayout(manual_row)

    def show_discovered(self, tvs: list[DiscoveredTV]):
        self._tv_list.clear()
        if not tvs:
            self._status_label.setText("No TVs found — ensure TV is on the same Wi-Fi network")
            return
        self._status_label.setText(f"{len(tvs)} TV(s) found")
        for tv in tvs:
            item = QListWidgetItem(f"{tv.name}  ({tv.ip})")
            item.setData(Qt.ItemDataRole.UserRole, tv)
            self._tv_list.addItem(item)

    def set_scanning(self, scanning: bool):
        self._scan_btn.setEnabled(not scanning)
        self._scan_btn.setText("Scanning…" if scanning else "Scan Network")

    def _on_scan_clicked(self):
        self.tv_selected.emit("__scan__", "")

    def _on_item_double_clicked(self, item: QListWidgetItem):
        tv: DiscoveredTV = item.data(Qt.ItemDataRole.UserRole)
        self.tv_selected.emit(tv.ip, tv.name)

    def _on_manual_connect(self):
        ip = self._ip_input.text().strip()
        if ip:
            self.tv_selected.emit(ip, ip)
