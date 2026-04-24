# app/tv/state.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ChipGeneration(Enum):
    UNKNOWN = "unknown"
    ALPHA9_GEN4 = "alpha9_gen4"   # C1 (2021)
    ALPHA9_GEN5 = "alpha9_gen5"   # C2 (2022)
    ALPHA9_GEN6 = "alpha9_gen6"   # C3 (2023)
    ALPHA9_GEN7 = "alpha9_gen7"   # C4 (2024)
    ALPHA9_GEN8 = "alpha9_gen8"   # C5 (2025)
    ALPHA9_GEN9 = "alpha9_gen9"   # C6 (2026) — chip name unconfirmed, update when hardware is released


WB_20PT_IRES = list(range(5, 105, 5))  # IRE steps: [5, 10, 15, ..., 100] — index 0 = 5% IRE


@dataclass
class TVSettingsSnapshot:
    # Identity
    chip_generation: ChipGeneration = ChipGeneration.UNKNOWN
    webos_version: str = ""
    pic_mode: str = "expert1"

    # Tab 1 — Picture
    oled_light: int = 50
    contrast: int = 85
    brightness: int = 50
    sharpness: int = 10
    color: int = 50
    tint: int = 0
    color_temperature: str = "warm2"

    # Tab 2 — White Balance 2-point
    wb_2pt_red_gain: int = 0
    wb_2pt_green_gain: int = 0
    wb_2pt_blue_gain: int = 0
    wb_2pt_red_offset: int = 0
    wb_2pt_green_offset: int = 0
    wb_2pt_blue_offset: int = 0

    # Tab 2 — White Balance 20-point (one value per IRE step 5%–100%)
    wb_20pt_red: list[int] = field(default_factory=lambda: [0] * 20)
    wb_20pt_green: list[int] = field(default_factory=lambda: [0] * 20)
    wb_20pt_blue: list[int] = field(default_factory=lambda: [0] * 20)

    # Tab 3 — Gamma / Color Space
    gamma: str = "bt1886"
    color_space: str = "auto"
    black_level: str = "low"
    trumotion: str = "off"

    # Tab 4 — CMS per-color (Hue/Saturation/Luminance)
    cms_red_hue: int = 0
    cms_red_saturation: int = 0
    cms_red_luminance: int = 0
    cms_green_hue: int = 0
    cms_green_saturation: int = 0
    cms_green_luminance: int = 0
    cms_blue_hue: int = 0
    cms_blue_saturation: int = 0
    cms_blue_luminance: int = 0
    cms_cyan_hue: int = 0
    cms_cyan_saturation: int = 0
    cms_cyan_luminance: int = 0
    cms_magenta_hue: int = 0
    cms_magenta_saturation: int = 0
    cms_magenta_luminance: int = 0
    cms_yellow_hue: int = 0
    cms_yellow_saturation: int = 0
    cms_yellow_luminance: int = 0

    # Tab 5 — HDR / Dynamic
    dynamic_contrast: str = "off"
    dynamic_color: str = "off"
    asbl: bool = False  # ASBL = Auto Segment Brightness Limiter (LG's automatic brightness limiter)
    hdr_tone_mapping: bool = False  # HDR tone mapping remaps signal curves during calibration
    peak_luminance: Optional[int] = None
    dv_picture_mode: str = "dark"  # Dolby Vision only — not active during SDR/HDR10 calibration
    local_dimming: str = "off"  # local dimming corrupts calibration measurements
    energy_saving: str = "off"
