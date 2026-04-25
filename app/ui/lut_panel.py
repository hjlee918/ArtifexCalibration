# app/ui/lut_panel.py
from __future__ import annotations
from typing import Callable, Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFileDialog, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt
from app.tv.lut import LUT1D, LUT3D, parse_cube, parse_cal
from app.tv.upload import LUTTarget

_STYLE_LABEL = "color: #ccc; font-size: 12px;"
_STYLE_BTN_PRIMARY = (
    "background: #4fc3f7; color: #000; padding: 8px 16px; border-radius: 4px; font-weight: bold;"
)
_STYLE_BTN_SECONDARY = "background: #2a2a3e; color: #aaa; padding: 6px 12px; border-radius: 4px;"
_STYLE_COMBO = "background: #1a1a2e; color: #ccc; border: 1px solid #333; padding: 4px 8px; border-radius: 4px;"
_GROUP_STYLE = (
    "QGroupBox { color: #aaa; font-size: 12px; border: 1px solid #333; border-radius: 4px; margin-top: 8px; }"
    "QGroupBox::title { padding: 0 4px; }"
)


class LUTPanel(QWidget):
    def __init__(self, on_upload: Callable, parent=None):
        super().__init__(parent)
        self._on_upload = on_upload
        self._loaded_lut: Optional[LUT1D | LUT3D] = None
        self._lut_path: Optional[Path] = None
        self._dv_path: Optional[Path] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("LUT Files")
        title.setStyleSheet("color: #fff; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # LUT file selection
        file_group = QGroupBox("LUT File")
        file_group.setStyleSheet(_GROUP_STYLE)
        file_layout = QVBoxLayout(file_group)

        file_row = QHBoxLayout()
        self._file_label = QLabel("No file selected")
        self._file_label.setStyleSheet("color: #aaa; font-size: 12px;")
        browse_btn = QPushButton("Browse…")
        browse_btn.setStyleSheet(_STYLE_BTN_SECONDARY)
        browse_btn.clicked.connect(self._on_browse)
        file_row.addWidget(self._file_label, 1)
        file_row.addWidget(browse_btn)
        file_layout.addLayout(file_row)

        self._lut_info_label = QLabel("")
        self._lut_info_label.setStyleSheet("color: #4fc3f7; font-size: 11px;")
        file_layout.addWidget(self._lut_info_label)
        layout.addWidget(file_group)

        # Upload options
        options_group = QGroupBox("Upload Options")
        options_group.setStyleSheet(_GROUP_STYLE)
        options_layout = QGridLayout(options_group)
        options_layout.setSpacing(10)

        options_layout.addWidget(self._lbl("Color Space Target:"), 0, 0)
        self._target_combo = QComboBox()
        self._target_combo.setStyleSheet(_STYLE_COMBO)
        self._target_combo.addItems(["BT.709 (SDR)", "BT.2020 (HDR10 / HLG)"])
        options_layout.addWidget(self._target_combo, 0, 1)

        options_layout.addWidget(self._lbl("Picture Mode:"), 1, 0)
        self._picmode_combo = QComboBox()
        self._picmode_combo.setStyleSheet(_STYLE_COMBO)
        self._picmode_combo.addItems(["expert1", "expert2", "cinema", "isf_bright", "isf_dark"])
        options_layout.addWidget(self._picmode_combo, 1, 1)

        layout.addWidget(options_group)

        # Dolby Vision Config
        dv_group = QGroupBox("Dolby Vision Config")
        dv_group.setStyleSheet(_GROUP_STYLE)
        dv_layout = QVBoxLayout(dv_group)

        dv_row = QHBoxLayout()
        self._dv_label = QLabel("No file selected")
        self._dv_label.setStyleSheet("color: #aaa; font-size: 12px;")
        dv_browse_btn = QPushButton("Browse…")
        dv_browse_btn.setStyleSheet(_STYLE_BTN_SECONDARY)
        dv_browse_btn.clicked.connect(self._on_browse_dv)
        dv_row.addWidget(self._dv_label, 1)
        dv_row.addWidget(dv_browse_btn)
        dv_layout.addLayout(dv_row)

        dv_upload_btn = QPushButton("Upload DV Config")
        dv_upload_btn.setStyleSheet(_STYLE_BTN_SECONDARY)
        dv_upload_btn.clicked.connect(self._on_upload_dv)
        dv_layout.addWidget(dv_upload_btn)
        layout.addWidget(dv_group)

        # Upload LUT button
        self._upload_btn = QPushButton("Upload LUT to TV")
        self._upload_btn.setStyleSheet(_STYLE_BTN_PRIMARY)
        self._upload_btn.setEnabled(False)
        self._upload_btn.clicked.connect(self._on_upload_clicked)
        layout.addWidget(self._upload_btn)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #4fc3f7; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(_STYLE_LABEL)
        return l

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select LUT File", "",
            "LUT Files (*.cube *.cal);;Cube (*.cube);;Cal (*.cal)"
        )
        if not path:
            return
        try:
            p = Path(path)
            if p.suffix.lower() == ".cube":
                self._loaded_lut = parse_cube(p)
                info = f"3D LUT — {self._loaded_lut.size}³ — {p.name}"
            elif p.suffix.lower() == ".cal":
                self._loaded_lut = parse_cal(p)
                info = f"1D LUT — {self._loaded_lut.data.shape[1]} pts — {p.name}"
            else:
                self.set_status(f"Unsupported file type: {p.suffix}", error=True)
                return
            self._lut_path = p
            self._file_label.setText(p.name)
            self._lut_info_label.setText(info)
            self._upload_btn.setEnabled(True)
            self.set_status("")
        except Exception as e:
            self.set_status(f"Parse error: {e}", error=True)

    def _on_browse_dv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Dolby Vision Config", "",
            "DV Config (*.txt *.cfg)"
        )
        if path:
            self._dv_path = Path(path)
            self._dv_label.setText(self._dv_path.name)

    def _on_upload_clicked(self):
        if self._loaded_lut is None:
            return
        target = LUTTarget.BT709 if "709" in self._target_combo.currentText() else LUTTarget.BT2020
        pic_mode = self._picmode_combo.currentText()
        self._on_upload(self._loaded_lut, target, pic_mode)

    def _on_upload_dv(self):
        if self._dv_path is None:
            return
        self._on_upload(self._dv_path, None, None)

    def set_status(self, text: str, error: bool = False) -> None:
        color = "#f44336" if error else "#4fc3f7"
        self._status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        self._status_label.setText(text)
