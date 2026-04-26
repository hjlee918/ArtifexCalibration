# app/ui/measurement_panel.py
from __future__ import annotations
import asyncio
from typing import Callable, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QGridLayout, QProgressBar, QLineEdit,
    QTextEdit
)
from PyQt6.QtCore import Qt
from app.meter.device import MeterDevice

_STYLE_LABEL = "color: #ccc; font-size: 12px;"
_STYLE_BTN_RUN = (
    "background: #4fc3f7; color: #000; padding: 10px 24px; border-radius: 4px; "
    "font-weight: bold; font-size: 13px;"
)
_STYLE_BTN_SEC = "background: #2a2a3e; color: #aaa; padding: 6px 12px; border-radius: 4px;"
_STYLE_COMBO = "background: #1a1a2e; color: #ccc; border: 1px solid #333; padding: 4px 8px; border-radius: 4px;"


class MeasurementPanel(QWidget):
    def __init__(self, on_run: Callable, on_upload_lut: Callable, parent=None):
        super().__init__(parent)
        self._on_run = on_run
        self._on_upload_lut = on_upload_lut
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Calibrate")
        title.setStyleSheet("color: #fff; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Device selection
        device_group = QGroupBox("Measurement Devices")
        device_group.setStyleSheet(
            "QGroupBox { color: #aaa; font-size: 12px; border: 1px solid #333; "
            "border-radius: 4px; margin-top: 8px; } QGroupBox::title { padding: 0 4px; }"
        )
        device_layout = QGridLayout(device_group)

        device_layout.addWidget(self._lbl("Meter:"), 0, 0)
        self._meter_combo = QComboBox()
        self._meter_combo.setStyleSheet(_STYLE_COMBO)
        self._meter_combo.addItem("— no meters detected —")
        device_layout.addWidget(self._meter_combo, 0, 1)

        scan_btn = QPushButton("Scan Meters")
        scan_btn.setStyleSheet(_STYLE_BTN_SEC)
        scan_btn.clicked.connect(self._on_scan_meters)
        device_layout.addWidget(scan_btn, 0, 2)

        device_layout.addWidget(self._lbl("Generator:"), 1, 0)
        self._gen_combo = QComboBox()
        self._gen_combo.setStyleSheet(_STYLE_COMBO)
        self._gen_combo.addItems(["iTPG (Internal)", "PGenerator (External)"])
        device_layout.addWidget(self._gen_combo, 1, 1)

        device_layout.addWidget(self._lbl("PGenerator IP:"), 2, 0)
        self._pgen_ip = QLineEdit("192.168.1.200")
        self._pgen_ip.setStyleSheet("background: #1a1a2e; color: #fff; border: 1px solid #333; padding: 4px; border-radius: 4px;")
        device_layout.addWidget(self._pgen_ip, 2, 1)

        layout.addWidget(device_group)

        # Sequence selection
        seq_group = QGroupBox("Measurement Sequence")
        seq_group.setStyleSheet(device_group.styleSheet())
        seq_layout = QGridLayout(seq_group)

        seq_layout.addWidget(self._lbl("Sequence:"), 0, 0)
        self._seq_combo = QComboBox()
        self._seq_combo.setStyleSheet(_STYLE_COMBO)
        self._seq_combo.addItems([
            "SDR Grayscale (21pt)",
            "SDR Full (grayscale + primaries + secondaries)",
            "HDR10 Grayscale",
            "HDR10 Full",
        ])
        seq_layout.addWidget(self._seq_combo, 0, 1)

        seq_layout.addWidget(self._lbl("Target Color Space:"), 1, 0)
        self._cs_combo = QComboBox()
        self._cs_combo.setStyleSheet(_STYLE_COMBO)
        self._cs_combo.addItems(["BT.709 (SDR)", "BT.2020 (HDR10)", "DCI-P3"])
        seq_layout.addWidget(self._cs_combo, 1, 1)

        layout.addWidget(seq_group)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet(
            "QProgressBar { background: #1a1a2e; border: 1px solid #333; border-radius: 4px; height: 12px; }"
            "QProgressBar::chunk { background: #4fc3f7; border-radius: 3px; }"
        )
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(self._status_label)

        # Run button row
        run_row = QHBoxLayout()
        self._run_btn = QPushButton("Start Measurement")
        self._run_btn.setStyleSheet(_STYLE_BTN_RUN)
        self._run_btn.clicked.connect(self._on_run_clicked)
        run_row.addWidget(self._run_btn)

        self._upload_btn = QPushButton("Generate & Upload LUT")
        self._upload_btn.setStyleSheet(_STYLE_BTN_SEC)
        self._upload_btn.setEnabled(False)
        self._upload_btn.clicked.connect(self._on_upload_clicked)
        run_row.addWidget(self._upload_btn)
        run_row.addStretch()
        layout.addLayout(run_row)

        # Log output
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            "background: #0d1117; color: #aaa; font-family: monospace; "
            "font-size: 11px; border: 1px solid #333; border-radius: 4px;"
        )
        self._log.setFixedHeight(150)
        layout.addWidget(self._log)

        layout.addStretch()

    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(_STYLE_LABEL)
        return l

    def populate_meters(self, devices: List[MeterDevice]):
        self._meter_combo.clear()
        if not devices:
            self._meter_combo.addItem("— no meters detected —")
            return
        for d in devices:
            self._meter_combo.addItem(f"{d.index}: {d.name}")

    def set_progress(self, current: int, total: int, label: str = ""):
        pct = int(current / total * 100) if total > 0 else 0
        self._progress_bar.setValue(pct)
        self._status_label.setText(f"Patch {current}/{total} — {label}")

    def log(self, text: str):
        self._log.append(text)

    def set_running(self, running: bool):
        self._run_btn.setEnabled(not running)
        self._run_btn.setText("Measuring…" if running else "Start Measurement")

    def enable_upload(self):
        self._upload_btn.setEnabled(True)

    def _on_scan_meters(self):
        self._on_run("__scan_meters__")

    def _on_run_clicked(self):
        gen_use_itpg = "iTPG" in self._gen_combo.currentText()
        pgen_ip = self._pgen_ip.text().strip()
        seq_name = self._seq_combo.currentText()
        self._on_run({
            "action": "measure",
            "use_itpg": gen_use_itpg,
            "pgen_ip": pgen_ip,
            "sequence": seq_name,
        })

    def _on_upload_clicked(self):
        self._on_upload_lut()
