# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Commands

- Install: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Unit tests (no TV): `pytest tests/unit/ -v`
- Hardware tests (TV required): `pytest tests/hardware/ -v -m hardware`
- Single test: `pytest tests/unit/test_discovery.py::test_discover_returns_found_tvs -v`
- Launch app: `python -m app.main`

## Architecture

Python + PyQt6 macOS desktop app for LG OLED C1–C6 calibration (2021–2026 models).

- `app/tv/` — TV communication layer: discovery (SSDP), connection (bscpylgtv wrapper), settings extension (raw SSAP), state cache
- `app/ui/` — PyQt6 UI: main window with sidebar, discovery panel, 5-tab settings panel
- `app/utils/` — macOS Keychain wrapper for client key storage
- `bscpylgtv` handles SSAP transport and calibration commands; `LGTVSettings` (app/tv/settings.py) adds picture settings bscpylgtv doesn't cover
- `qasync` bridges asyncio and the PyQt6 event loop

## Sub-projects

- Sub-project 1 (this): TV discovery, connection, full expert picture menu read/write
- Sub-project 2: LUT upload pipeline (1D/3D, SDR/HDR10/DV)
- Sub-project 3: Measurement workflow + LUT generation (X-Rite meters, LightSpace Pi)
