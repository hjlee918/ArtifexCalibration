# app/ui/settings_panel.py
from typing import Callable, Coroutine
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QSlider, QComboBox, QPushButton, QGridLayout,
    QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt
from app.tv.state import TVSettingsSnapshot

_STYLE_SLIDER = (
    "QSlider::groove:horizontal { height: 6px; background: #2a2a3e; border-radius: 3px; }"
    "QSlider::handle:horizontal { background: #4fc3f7; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; }"
    "QSlider::sub-page:horizontal { background: #4fc3f7; border-radius: 3px; }"
)
_STYLE_COMBO = "background: #1a1a2e; color: #ccc; border: 1px solid #333; padding: 4px 8px; border-radius: 4px;"
_STYLE_LABEL = "color: #ccc; font-size: 12px;"
_STYLE_SECTION = "color: #fff; font-size: 13px; font-weight: bold; background: transparent;"


def _labeled_slider(label: str, min_v: int, max_v: int, value: int,
                    obj_name: str, on_change: Callable) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(label)
    lbl.setFixedWidth(130)
    lbl.setStyleSheet(_STYLE_LABEL)
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(min_v, max_v)
    slider.setValue(value)
    slider.setObjectName(obj_name)
    slider.setStyleSheet(_STYLE_SLIDER)
    val_label = QLabel(str(value))
    val_label.setFixedWidth(36)
    val_label.setStyleSheet("color: #4fc3f7; font-size: 12px;")
    slider.valueChanged.connect(lambda v: val_label.setText(str(v)))
    slider.valueChanged.connect(on_change)
    layout.addWidget(lbl)
    layout.addWidget(slider, 1)
    layout.addWidget(val_label)
    return row


def _labeled_combo(label: str, options: list[str], current: str,
                   on_change: Callable) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(label)
    lbl.setFixedWidth(130)
    lbl.setStyleSheet(_STYLE_LABEL)
    combo = QComboBox()
    combo.setStyleSheet(_STYLE_COMBO)
    for opt in options:
        combo.addItem(opt)
    idx = combo.findText(current, Qt.MatchFlag.MatchFixedString)
    if idx >= 0:
        combo.setCurrentIndex(idx)
    combo.currentTextChanged.connect(on_change)
    layout.addWidget(lbl)
    layout.addWidget(combo, 1)
    return row


class SettingsPanel(QWidget):
    def __init__(self, snapshot: TVSettingsSnapshot,
                 on_write: Callable[[Coroutine], None], parent=None):
        super().__init__(parent)
        self._snap = snapshot
        self._on_write = on_write
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            "QTabWidget::pane { background: #111; border: none; }"
            "QTabBar::tab { background: #1a1a2e; color: #aaa; padding: 8px 16px; border: none; }"
            "QTabBar::tab:selected { background: #2a2a3e; color: #fff; border-bottom: 2px solid #4fc3f7; }"
        )
        self._tabs.addTab(self._build_picture_tab(), "Picture")
        self._tabs.addTab(self._build_white_balance_tab(), "White Balance")
        self._tabs.addTab(self._build_gamma_tab(), "Gamma / Color Space")
        self._tabs.addTab(self._build_cms_tab(), "Color Management")
        self._tabs.addTab(self._build_hdr_tab(), "HDR / Dynamic")
        layout.addWidget(self._tabs)

    def _scrollable(self, inner: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: #111; border: none;")
        scroll.setWidget(inner)
        return scroll

    def _noop(self):
        async def _inner():
            pass
        return _inner()

    def _build_picture_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: #111;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        s = self._snap
        layout.addWidget(_labeled_slider("OLED Light", 0, 100, s.oled_light, "oled_light",
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_slider("Contrast", 0, 100, s.contrast, "contrast",
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_slider("Brightness", 0, 100, s.brightness, "brightness",
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_slider("Sharpness", 0, 50, s.sharpness, "sharpness",
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_slider("Color", 0, 100, s.color, "color",
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_slider("Tint", -10, 10, s.tint, "tint",
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("Color Temperature",
            ["Warm 50", "Warm", "Natural", "Cool", "Manual"],
            s.color_temperature, lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("Picture Mode",
            ["expert1", "expert2", "cinema", "isf_bright", "isf_dark"],
            s.pic_mode, lambda v: self._on_write(self._noop())))
        layout.addStretch()
        return self._scrollable(w)

    def _build_white_balance_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: #111;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        s = self._snap
        lbl = QLabel("2-Point White Balance")
        lbl.setStyleSheet(_STYLE_SECTION)
        layout.addWidget(lbl)
        for label, obj, val in [
            ("Red Gain", "wb_2pt_red_gain", s.wb_2pt_red_gain),
            ("Green Gain", "wb_2pt_green_gain", s.wb_2pt_green_gain),
            ("Blue Gain", "wb_2pt_blue_gain", s.wb_2pt_blue_gain),
            ("Red Offset", "wb_2pt_red_offset", s.wb_2pt_red_offset),
            ("Green Offset", "wb_2pt_green_offset", s.wb_2pt_green_offset),
            ("Blue Offset", "wb_2pt_blue_offset", s.wb_2pt_blue_offset),
        ]:
            layout.addWidget(_labeled_slider(label, -50, 50, val, obj,
                lambda v: self._on_write(self._noop())))
        btn_row = QHBoxLayout()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setStyleSheet("background: #2a2a3e; color: #aaa; padding: 6px 12px; border-radius: 4px;")
        copy_btn = QPushButton("Copy C1 → C2")
        copy_btn.setStyleSheet("background: #2a2a3e; color: #aaa; padding: 6px 12px; border-radius: 4px;")
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()
        return self._scrollable(w)

    def _build_gamma_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: #111;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        s = self._snap
        gamma_map = {"1.8": "1.8", "2.0": "2.0", "2.2": "2.2", "2.4": "2.4",
                     "BT.1886": "bt1886", "sRGB": "srgb"}
        gamma_display = next((k for k, v in gamma_map.items() if v == s.gamma), "BT.1886")
        layout.addWidget(_labeled_combo("Gamma", list(gamma_map.keys()), gamma_display,
            lambda v: self._on_write(self._noop())))
        cs_map = {"Auto": "auto", "Native": "native", "BT.709": "bt709",
                  "BT.2020": "bt2020", "DCI-P3": "dcip3"}
        cs_display = next((k for k, v in cs_map.items() if v == s.color_space), "Auto")
        layout.addWidget(_labeled_combo("Color Space", list(cs_map.keys()), cs_display,
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("Black Level", ["Low", "High", "Auto"],
            s.black_level.capitalize(), lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("TruMotion", ["Off", "Smooth", "Clear", "User"],
            s.trumotion.capitalize(), lambda v: self._on_write(self._noop())))
        layout.addStretch()
        return self._scrollable(w)

    def _build_cms_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: #111;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        s = self._snap
        layout.addWidget(_labeled_combo("Color",
            ["Red", "Green", "Blue", "Cyan", "Magenta", "Yellow"],
            "Red", lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_slider("Hue", -30, 30, s.cms_red_hue, "cms_hue",
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_slider("Saturation", -30, 30, s.cms_red_saturation, "cms_sat",
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_slider("Luminance", -30, 30, s.cms_red_luminance, "cms_lum",
            lambda v: self._on_write(self._noop())))
        btn_row = QHBoxLayout()
        for label in ("Reset Color", "Reset All Colors"):
            btn = QPushButton(label)
            btn.setStyleSheet("background: #2a2a3e; color: #aaa; padding: 6px 12px; border-radius: 4px;")
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()
        return self._scrollable(w)

    def _build_hdr_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: #111;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        s = self._snap
        layout.addWidget(_labeled_combo("Dynamic Contrast", ["Off", "Low", "Medium", "High"],
            s.dynamic_contrast.capitalize(), lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("Dynamic Color", ["Off", "Low", "High"],
            s.dynamic_color.capitalize(), lambda v: self._on_write(self._noop())))
        asbl_row = QHBoxLayout()
        asbl_lbl = QLabel("ASBL")
        asbl_lbl.setFixedWidth(130)
        asbl_lbl.setStyleSheet(_STYLE_LABEL)
        asbl_check = QCheckBox()
        asbl_check.setChecked(s.asbl)
        asbl_check.stateChanged.connect(lambda v: self._on_write(self._noop()))
        asbl_row.addWidget(asbl_lbl)
        asbl_row.addWidget(asbl_check)
        asbl_row.addStretch()
        layout.addLayout(asbl_row)
        layout.addWidget(_labeled_combo("HDR Tone Mapping", ["On", "Off"],
            "On" if s.hdr_tone_mapping else "Off", lambda v: self._on_write(self._noop())))
        peak_val = s.peak_luminance if s.peak_luminance is not None else 1000
        layout.addWidget(_labeled_slider("Peak Luminance (nits)", 100, 4000, peak_val,
            "peak_luminance", lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("DV Picture Mode", ["Bright", "Dark", "Vivid"],
            s.dv_picture_mode.capitalize(), lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("Local Dimming", ["Off", "Low", "Medium", "High"],
            s.local_dimming.capitalize(), lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("Energy Saving",
            ["Off", "Min", "Med", "Max", "Auto", "Screen Off"],
            s.energy_saving.capitalize(), lambda v: self._on_write(self._noop())))
        layout.addStretch()
        return self._scrollable(w)

    def set_connection(self, mgr, lgtv_settings):
        self._mgr = mgr
        self._lgtv = lgtv_settings
