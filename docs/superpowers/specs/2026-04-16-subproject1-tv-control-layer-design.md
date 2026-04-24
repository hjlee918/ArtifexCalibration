# Sub-project 1: TV Control Layer — Design Spec

**Date:** 2026-04-16 (updated 2026-04-23)  
**Project:** LG OLED Calibration App  
**Scope:** TV discovery, connection, pairing, and full Expert/Advanced picture menu read/write for LG OLED 2021–2026 models (C1–C6, G1–G6, B1–B6, Z1–Z6, A-series)  
**Platform:** macOS desktop app — Python + PyQt6  
**Depends on:** nothing (foundational layer)  
**Followed by:** Sub-project 2 (LUT upload pipeline), Sub-project 3 (measurement & LUT generation)

---

## Overview

A macOS desktop application that wirelessly connects to LG OLED C1 and C2 TVs over WebSocket/SSAP and exposes full Expert/Advanced picture menu control. This is the foundational layer all subsequent calibration functionality sits on top of.

The app uses `bscpylgtv` for SSAP transport and calibration commands, extended by a custom `LGTVSettings` module for the full expert picture menu settings that `bscpylgtv` does not cover.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PyQt6 App Shell                             │
│  ┌──────────────────┐   ┌──────────────────────────────────┐   │
│  │  Discovery Panel │   │       Settings Panel              │   │
│  │  • Scan network  │   │  Tabs: Picture | White Balance   │   │
│  │  • List found TVs│   │  Gamma/CS | Color Mgmt | HDR     │   │
│  │  • Pair / Connect│   └──────────────┬───────────────────┘   │
│  └────────┬─────────┘                  │                        │
└───────────┼────────────────────────────│────────────────────────┘
            │                            │
            ▼                            ▼
┌───────────────────────┐    ┌───────────────────────────────┐
│   Connection Manager  │    │   LGTVSettings Extension      │
│  (wraps bscpylgtv)    │◄───│   (raw SSAP payloads)         │
│  • SSAP WebSocket     │    │   • Expert menu settings      │
│  • Pairing + Keychain │    │   • White balance fine-tune   │
│  • Calibration cmds   │    │   • CMS per-color controls    │
│  • LUT upload (SP2)   │    │   • HDR tone mapping params   │
└───────────┬───────────┘    └───────────────────────────────┘
            │
            ▼
┌───────────────────────┐    ┌───────────────────────────────┐
│   Discovery Service   │    │   TV State Cache              │
│  • SSDP M-SEARCH      │    │   • TVSettingsSnapshot per TV │
│  • UDP multicast      │    │   • Populated on connect      │
│  • Returns IP + model │    │   • C1 vs C2 model detection  │
└───────────────────────┘    └───────────────────────────────┘
            │
            ▼
    LG OLED C1 / C2  (WebSocket port 3000 / 3001)
```

---

## Components

### Discovery Service

- Sends SSDP M-SEARCH to `udp://239.255.255.250:1900` with service type `urn:lge-com:service:webos-second-screen:1`
- Parses responses to extract TV IP address and friendly name
- Returns a list of `DiscoveredTV(ip, name)` for display in the sidebar
- Scan can be triggered manually or on app launch

### Connection Manager

Wraps `bscpylgtv.WebOsClient`. Responsibilities:

- **Pairing:** On first connect, initiates WebSocket handshake; TV displays PIN. Client key returned is stored in macOS Keychain via `keyring` library keyed by TV IP address.
- **Reconnect:** On subsequent launches, loads client key from Keychain and connects silently.
- **Model detection:** Calls `get_software_info` on connect; parses `model_name` to determine Alpha 9 Gen4 (C1) vs Alpha 9 Gen5 (C2). Stores as `chip_generation` on the connection object for payload routing.
- **Firmware check:** Reads `webos_version` from `get_software_info`; warns user if webOS ≥ 7.3 (known calibration API breakage).
- **Dual-TV support:** Both C1 and C2 can be connected simultaneously; each has an independent `WebOsClient` instance and `TVSettingsSnapshot`.
- **Reconnect logic:** On connection loss, auto-reconnects with exponential backoff (3 attempts: 2s, 4s, 8s). Sidebar badge shows "Reconnecting…" state.

### LGTVSettings Extension

Sends raw SSAP payloads via `ssap://externalpq/setExternalPqData` and reads via `ssap://externalpq/getExternalPqData` for settings not exposed by `bscpylgtv`. All calls include the active `picMode` parameter (e.g., `expert1`, `expert2`) so settings are scoped to the correct picture mode.

Covers settings not exposed by `bscpylgtv`:
- Full 2-point and 20-point white balance (R/G/B gain and offset per IRE step)
- CMS per-color (Red/Green/Blue/Cyan/Magenta/Yellow × Hue/Saturation/Luminance)
- Dynamic Contrast, Dynamic Color, ASBL, Local Dimming, Energy Saving

The following are already in `bscpylgtv` and called directly through Connection Manager (not re-implemented):
- 3×3 gamut matrix (`set_3by3_gamut_data`)
- HDR tone mapping parameters (`set_tonemap_params`)

### TV State Cache

- `TVSettingsSnapshot` is a dataclass holding the current value of every expert setting for a given TV + picture mode combination.
- Populated via a batch read on connect and on picture mode switch.
- UI controls bind to snapshot values. Writes update the snapshot locally after a successful SSAP write (TV is the source of truth; snapshot is a local mirror to avoid round-trip reads on every slider drag).
- No persistence to disk — snapshot is rebuilt from TV on each connection.

---

## UI Layout

**Sidebar + Tabbed Settings** (Option A):

```
┌──────────────┬─────────────────────────────────────────────┐
│  Sidebar     │  Settings Panel                             │
│              │  [Picture][White Bal][Gamma/CS][CMS][HDR]  │
│ ● C1 Connected│                                            │
│ ○ C2 Offline │  ← Active tab content →                   │
│ ─────────── │                                             │
│ 📺 Settings  │                                             │
│ 🎨 Calibrate │                                             │
│ 📁 LUT Files │                                             │
│ ⚙️  Prefs    │                                             │
└──────────────┴─────────────────────────────────────────────┘
```

### Settings Tabs

**Tab 1 — Picture**
- OLED Light (0–100), Contrast (0–100), Brightness (0–100)
- Sharpness (0–50), Color (0–100), Tint (R0–G0)
- Color Temperature: Warm50 / Warm / Natural / Cool / Manual
- Picture Mode selector: Expert1 / Expert2 / Cinema / ISF Bright / ISF Dark

**Tab 2 — White Balance**
- Method toggle: 2-Point ↔ 20-Point
- 2pt: Red/Green/Blue Gain + Offset sliders
- 20pt: per-IRE (5%–100%) R/G/B offset inputs
- Reset to defaults button
- Copy settings C1 → C2 (or C2 → C1)

**Tab 3 — Gamma / Color Space**
- Gamma: 1.8 / 2.0 / 2.2 / 2.4 / BT.1886 / sRGB
- Color Space: Auto / Native / BT.709 / BT.2020 / DCI-P3
- Black Level: Low / High (Auto)
- TruMotion / Motion Eye Care

**Tab 4 — Color Management (CMS)**
- Color selector: Red / Green / Blue / Cyan / Magenta / Yellow
- Per-color: Hue, Saturation, Luminance sliders
- Reset individual color or all
- 3×3 Gamut matrix inputs

**Tab 5 — HDR / Dynamic**
- Dynamic Contrast: Off / Low / Medium / High
- Dynamic Color: Off / Low / High
- ASBL (Auto Static Brightness Limiter): On / Off
- HDR Tone Mapping: On / Off
- Peak Luminance target (nits, HDR10)
- Dolby Vision Picture Mode: Bright / Dark / Vivid
- Local Dimming: Off / Low / Medium / High
- Energy Saving: Off / Min / Med / Max / Auto / Screen Off

---

## Data Flow

1. App launch → Discovery Service scans network → sidebar lists found TVs
2. User clicks TV → Connection Manager initiates WebSocket → TV shows PIN → user enters PIN → client key stored in Keychain
3. On successful pairing: `get_software_info` → model detection → batch settings read → `TVSettingsSnapshot` populated → UI controls enabled
4. User adjusts a setting → UI writes to `LGTVSettings` extension or `bscpylgtv` → SSAP payload sent → on success, snapshot updated locally
5. Picture mode switch → batch re-read → snapshot refreshed → UI re-bound to new values

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Connection loss | Auto-reconnect (3×, exponential backoff). Sidebar shows "Reconnecting…" |
| SSAP error response | Inline status message in settings panel. No modal dialogs. |
| webOS ≥ 7.3 detected | Warning banner on connect: "Firmware may be incompatible with calibration commands" |
| Pairing key mismatch | Clears Keychain entry, re-initiates pairing flow |
| TV not found on scan | "No TVs found — ensure TV is on the same network" message with manual IP entry fallback |

---

## Project Structure

```
lg-oled-calibration/
├── app/
│   ├── main.py                  # PyQt6 entry point
│   ├── ui/
│   │   ├── main_window.py       # App shell, sidebar, navigation
│   │   ├── discovery_panel.py   # SSDP scan UI
│   │   └── settings_panel.py    # Tabbed settings UI
│   ├── tv/
│   │   ├── discovery.py         # SSDP service
│   │   ├── connection.py        # Connection Manager (bscpylgtv wrapper)
│   │   ├── settings.py          # LGTVSettings extension
│   │   └── state.py             # TVSettingsSnapshot dataclass
│   └── utils/
│       └── keychain.py          # macOS Keychain wrapper (keyring)
├── tests/
│   ├── unit/
│   │   ├── test_discovery.py
│   │   ├── test_settings.py
│   │   └── test_state.py
│   └── hardware/                # @pytest.mark.hardware — requires real TV
│       └── test_connection.py
├── Resources/                   # Calibration reference PDFs
├── docs/
│   └── superpowers/specs/
├── requirements.txt
└── CLAUDE.md
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `bscpylgtv` | SSAP transport, calibration commands, LUT upload |
| `PyQt6` | macOS desktop UI framework |
| `keyring` | macOS Keychain storage for client keys |
| `websockets` | Underlying WebSocket transport (used by bscpylgtv) |
| `pytest` | Test runner |

---

## Testing Strategy

- **Unit tests:** `bscpylgtv` interaction mocked at the WebSocket layer. `LGTVSettings` extension tested against recorded SSAP response fixtures from C1 and C2.
- **Hardware tests:** Full connection, pairing, and settings read/write against real TVs. Marked `@pytest.mark.hardware`, excluded from CI.
- **UI tests:** Settings panel binding tested with a mock `TVSettingsSnapshot` — no TV or network required.

---

## LG OLED Model / Chip / webOS Support Matrix

The `ChipGeneration` enum and `_detect_chip()` function in `app/tv/connection.py` must cover the full 2021–2026 lineup. Model detection uses the `model_name` string returned by `get_software_info()` (e.g., `"OLED65C1PUB"`, `"OLED77C2PUA"`, `"OLED83G4PSA"`).

| Year | Model Suffix | Chip Generation | webOS major_ver (approx.) |
|---|---|---|---|
| 2021 | C1, G1, Z1, B1, A1 | Alpha 9 Gen 4 | 6 |
| 2022 | C2, G2, Z2, B2, A2 | Alpha 9 Gen 5 | 22 |
| 2023 | C3, G3, Z3, B3, A3 | Alpha 9 Gen 6 | 23 |
| 2024 | C4, G4, Z4, B4, A4 | Alpha 9 Gen 7 | 24 |
| 2025 | C5, G5, Z5, B5, A5 | Alpha 9 Gen 8 | 25 |
| 2026 | C6, G6, Z6, B6, A6 | Alpha 9 Gen 9 (est.) | 26 (est.) |

**webOS version numbering note:** LG changed from semantic versioning to calendar year numbering in 2022. The `major_ver` field in `get_software_info()` returns `"6"` for 2021 models and `"22"`, `"23"`, etc. for subsequent years. The "webOS 7.3" incompatibility flag in the original plan refers specifically to a beta/interim 2021 C1 firmware that reported `major_ver="7"` — not the 2022+ calendar scheme. The firmware check logic must handle both: treat `major_ver >= 7 AND major_ver < 20` as the problematic range (2021 late firmware), while `major_ver >= 22` represents normal 2022+ models that need separate compatibility verification per year.

**Chip-specific routing:** Some SSAP payload keys differ between chip generations (e.g., local dimming, tone mapping precision, Dolby Vision metadata). The `chip_generation` field on `TVSettingsSnapshot` and `ConnectionManager` is the mechanism for routing chip-specific commands — sub-projects 2 and 3 will use it.

**2023+ models note:** From C3/G3 onward, LG added a second 3D LUT slot for Filmmaker Mode. The LUT upload pipeline (Sub-project 2) will need to handle this when targeting 2023+ chips. Flag it here so the architecture anticipates it.

---

## Out of Scope for Sub-project 1

- LUT upload (1D/3D, SDR/HDR10/DV) → Sub-project 2
- Colorimeter/spectrophotometer integration → Sub-project 3
- Measurement workflow and LUT generation → Sub-project 3
- Pattern generator (LightSpace/PGenerator Pi) integration → Sub-project 3
