# LG OLED Calibration App — Project Overview

**Date:** 2026-04-23  
**Platform:** macOS desktop app — Python + PyQt6  
**Goal:** A Calman-equivalent display calibration application for LG OLED TVs (2021–2026 model years), covering device control, LUT upload, colorimetric measurement, and LUT generation.

---

## What This App Does

The app connects to LG OLED TVs wirelessly and calibrates them end-to-end:

1. **Connects to the TV** over WebSocket/SSAP, reads and writes all Expert/Advanced picture settings, and uploads 1D/3D LUTs and Dolby Vision configs directly to the display pipeline
2. **Drives test patterns** via the TV's internal pattern generator (iTPG) or an external Raspberry Pi running PGenerator 1.6
3. **Reads the display** with an X-Rite i1 Display Pro or i1 Pro 2 via ArgyllCMS
4. **Generates correction LUTs** from the measurements and uploads them back to the TV

The result is a fully calibrated display with correct tone curve, accurate white point, and accurate color gamut — all without a commercial software license.

---

## Sub-project Map

```
Sub-project 1 — TV Control Layer          [PLAN WRITTEN, NOT YET IMPLEMENTED]
  TV discovery (SSDP), WebSocket/SSAP connection, Expert menu read/write,
  macOS Keychain pairing, model detection for 2021–2026 OLEDs

Sub-project 2 — LUT Upload Pipeline       [PLAN WRITTEN, NOT YET IMPLEMENTED]
  .cube / .cal file parsing, 1D + 3D LUT upload via bscpylgtv,
  Dolby Vision config (.cfg/.txt) upload, LUT management UI

Sub-project 3 — Measurement Workflow      [PLAN WRITTEN, NOT YET IMPLEMENTED]
  ArgyllCMS meter integration (i1 Display Pro, i1 Pro 2),
  iTPG + PGenerator 1.6 pattern generator control,
  patch sequence automation, CGATS/JSON storage,
  1D tone curve + 3D LUT generation from measurements
```

Dependencies flow in one direction: SP2 and SP3 both depend on SP1 being complete. SP3 optionally calls SP2 to upload generated LUTs directly.

---

## Hardware Targets

| Hardware | Role | Integration |
|---|---|---|
| LG OLED C1 (2021) | Primary calibration target | bscpylgtv via SSAP |
| LG OLED C2 (2022) | Secondary calibration target | bscpylgtv via SSAP |
| LG OLED C3–C6 (2023–2026) | Extended targets (verified on connect) | bscpylgtv via SSAP |
| LG OLED G1–G5, B1–B5, Z1–Z5 | Gallery/Signature series | Same SSAP stack |
| X-Rite i1 Display Pro Rev. B | Colorimeter (fast, 2000 nit EDR) | ArgyllCMS |
| X-Rite i1 Pro 2 | Spectrophotometer (reference accuracy) | ArgyllCMS |
| Raspberry Pi 4 + PGenerator 1.6 | External pattern generator | HTTP API |
| LG OLED iTPG | Internal pattern generator | bscpylgtv SSAP |

---

## LG OLED Model / Chip / webOS Reference (2021–2026)

This table drives model detection in Sub-project 1 and conditions chip-specific API routing in Sub-projects 2 and 3.

| Year | Model Series | Chip | webOS | Calibration Status |
|---|---|---|---|---|
| 2021 | C1, G1, Z1, B1 | Alpha 9 Gen 4 | 6.0 | Fully supported |
| 2022 | C2, G2, Z2, B2 | Alpha 9 Gen 5 | 22 | Fully supported |
| 2023 | C3, G3, Z3, B3 | Alpha 9 Gen 6 | 23 | Supported — verify firmware |
| 2024 | C4, G4, Z4, B4 | Alpha 9 Gen 7 | 24 | Supported — verify firmware |
| 2025 | C5, G5, Z5, B5 | Alpha 9 Gen 8 | 25 | Supported — verify firmware |
| 2026 | C6, G6, Z6, B6 | Alpha 9 Gen 9 (est.) | 26 (est.) | Unknown — test on connect |

**webOS version note:** LG changed version numbering from `6.x` to calendar-year format (`22`, `23`, ...) starting in 2022. The "webOS 7.3" breakage mentioned in SP1 refers to an interim firmware on 2021 C1 models with major_ver=7 in `get_software_info` — not the 2022+ calendar versioning system. The firmware check must use the raw `major_ver`/`minor_ver` strings from `get_software_info`, not assumed LG webOS branding versions.

---

## Full System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        PyQt6 App Shell                           │
│                                                                  │
│  Sidebar Nav           Content Area (QStackedWidget)            │
│  ─────────────         ────────────────────────────             │
│  ● C1 Connected  →     [Discovery] [Settings] [Calibrate]       │
│  ○ C2 Offline          [LUT Files] [Prefs]                      │
└───────────────┬───────────────┬──────────────────┬──────────────┘
                │               │                  │
     ┌──────────▼──────┐  ┌─────▼──────┐  ┌───────▼──────────┐
     │  Sub-project 1  │  │  SP2       │  │  Sub-project 3   │
     │  TV Control     │  │  LUT Upload│  │  Measurement     │
     │  ─────────────  │  │  ─────────-│  │  ────────────    │
     │  ConnectionMgr  │  │  LUTParser │  │  MeterDevice     │
     │  LGTVSettings   │  │  Uploader  │  │  ArgyllCMS       │
     │  Discovery      │  │  DV Config │  │  iTPG/PGenerator │
     │  TVSnapshot     │  │  LUT Panel │  │  PatchSequence   │
     └────────┬────────┘  └─────┬──────┘  │  MeasurSession   │
              │                 │         │  LUTGenerator    │
              └────────┬────────┘         └───────┬──────────┘
                       │                          │
              ┌────────▼──────────────────────────▼──────────┐
              │           bscpylgtv / WebOsClient             │
              │           SSAP over WebSocket                  │
              └───────────────────┬───────────────────────────┘
                                  │
              ┌───────────────────▼───────────────────────────┐
              │          LG OLED TV (2021–2026)               │
              │          WebSocket ports 3000 / 3001           │
              └───────────────────────────────────────────────┘

              ┌───────────────────────────────────────────────┐
              │  Meter Layer (Sub-project 3)                  │
              │  ArgyllCMS (spotread / dispread subprocess)   │
              │  → i1 Display Pro Rev. B  (USB)               │
              │  → i1 Pro 2               (USB)               │
              └───────────────────────────────────────────────┘

              ┌───────────────────────────────────────────────┐
              │  External Pattern Generator (Sub-project 3)   │
              │  PGenerator 1.6 HTTP API on Raspberry Pi 4    │
              └───────────────────────────────────────────────┘
```

---

## Calibration Workflow (End-to-End)

```
1. Connect TV (SP1)
      ↓
2. Select picture mode + color space + HDR format
      ↓
3. Select pattern generator (iTPG or PGenerator on Pi)
      ↓
4. Select meter (i1 Display Pro or i1 Pro 2)
      ↓
5. Run pre-calibration measurement (SP3)
      → Display 21-point grayscale + primaries + secondaries
      → Record XYZ readings per patch
      ↓
6. Generate correction LUTs (SP3)
      → 1D tone curve from grayscale
      → 3D LUT from full patch set
      ↓
7. Upload LUTs to TV (SP2)
      → 1D LUT via bscpylgtv
      → 3D LUT via bscpylgtv
      → Optional: DV config for Dolby Vision mode
      ↓
8. Run post-calibration verification measurement (SP3)
      → Compare against target (BT.709, DCI-P3, BT.2020)
      → Report ΔE2000 per patch
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| UI framework | PyQt6 |
| Async bridge | qasync |
| TV communication | bscpylgtv |
| Meter communication | ArgyllCMS (subprocess) |
| Pattern generation | iTPG (SSAP) + PGenerator (HTTP) |
| Keychain storage | keyring (macOS Keychain) |
| Numeric processing | numpy |
| Color science | colour-science (for ΔE, gamut math) |
| Testing | pytest, pytest-asyncio, pytest-qt |

---

## Plan Files

| Sub-project | Spec | Plan |
|---|---|---|
| 1 — TV Control Layer | `docs/superpowers/specs/2026-04-16-subproject1-tv-control-layer-design.md` | `docs/superpowers/plans/2026-04-16-subproject1-tv-control-layer.md` |
| 2 — LUT Upload Pipeline | *(see this overview)* | `docs/superpowers/plans/2026-04-23-subproject2-lut-upload-pipeline.md` |
| 3 — Measurement Workflow | *(see this overview)* | `docs/superpowers/plans/2026-04-23-subproject3-measurement-workflow.md` |
