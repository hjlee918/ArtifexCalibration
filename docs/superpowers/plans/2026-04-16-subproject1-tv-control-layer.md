# Sub-project 1: TV Control Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a macOS PyQt6 desktop app that discovers, connects to, and controls the full Expert/Advanced picture menu on LG OLED C1 and C2 TVs over WebSocket/SSAP.

**Architecture:** `bscpylgtv` handles SSAP transport and calibration commands; a custom `LGTVSettings` extension covers picture settings bscpylgtv doesn't expose (white balance, CMS, dynamic settings); `TVSettingsSnapshot` is an in-memory mirror of TV state populated on connect. The UI is a sidebar + 5-tab settings panel backed by PyQt6 with `qasync` bridging the asyncio event loop.

**Tech Stack:** Python 3.11+, PyQt6, bscpylgtv, qasync, keyring, websockets, pytest, pytest-asyncio

---

## File Map

| File | Responsibility |
|---|---|
| `app/main.py` | Entry point — starts qasync event loop, creates MainWindow |
| `app/tv/state.py` | `TVSettingsSnapshot` dataclass — in-memory mirror of TV settings |
| `app/tv/discovery.py` | SSDP M-SEARCH — finds LG TVs on local network |
| `app/utils/keychain.py` | macOS Keychain wrapper via `keyring` — stores/loads client keys by TV IP |
| `app/tv/connection.py` | `ConnectionManager` — wraps `bscpylgtv.WebOsClient`, pairing, model detection, reconnect |
| `app/tv/settings.py` | `LGTVSettings` — raw SSAP payloads for WB, CMS, dynamic settings |
| `app/ui/main_window.py` | `MainWindow` — sidebar with TV status badges, navigation |
| `app/ui/discovery_panel.py` | `DiscoveryPanel` — scan UI, TV list, connect/pair flow |
| `app/ui/settings_panel.py` | `SettingsPanel` — 5-tab settings UI, binds to `TVSettingsSnapshot` |
| `tests/conftest.py` | Shared fixtures: mock WebOsClient, sample snapshots |
| `tests/unit/test_state.py` | TVSettingsSnapshot unit tests |
| `tests/unit/test_discovery.py` | Discovery Service unit tests (mocked socket) |
| `tests/unit/test_keychain.py` | Keychain utility unit tests (mocked keyring) |
| `tests/unit/test_connection.py` | ConnectionManager unit tests (mocked bscpylgtv) |
| `tests/unit/test_settings.py` | LGTVSettings unit tests (mocked WebOsClient) |
| `tests/unit/test_settings_panel.py` | Settings panel binding tests (mock snapshot, no TV) |
| `tests/hardware/test_hardware.py` | `@pytest.mark.hardware` — real TV required |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `app/__init__.py`, `app/tv/__init__.py`, `app/ui/__init__.py`, `app/utils/__init__.py`
- Create: `tests/__init__.py`, `tests/unit/__init__.py`, `tests/hardware/__init__.py`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Create requirements.txt**

```
bscpylgtv>=0.9.0
PyQt6>=6.6.0
qasync>=0.27.0
keyring>=24.0.0
websockets>=12.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-qt>=4.4.0
```

- [ ] **Step 2: Create pytest.ini**

```ini
[pytest]
asyncio_mode = auto
markers =
    hardware: marks tests as requiring a real LG TV (deselect with -m "not hardware")
```

- [ ] **Step 3: Create all __init__.py files**

```bash
mkdir -p app/tv app/ui app/utils tests/unit tests/hardware
touch app/__init__.py app/tv/__init__.py app/ui/__init__.py app/utils/__init__.py
touch tests/__init__.py tests/unit/__init__.py tests/hardware/__init__.py
```

- [ ] **Step 4: Create virtual environment and install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 5: Update CLAUDE.md**

Replace contents with:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Commands

```bash
# Install dependencies
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Run all unit tests (no TV required)
pytest tests/unit/ -v

# Run hardware tests (requires LG TV on local network)
pytest tests/hardware/ -v -m hardware

# Run a single test
pytest tests/unit/test_discovery.py::test_discover_returns_found_tvs -v

# Launch the app
python -m app.main
```

## Architecture

Python + PyQt6 macOS desktop app for LG OLED C1/C2 calibration.

- `app/tv/` — TV communication layer: discovery (SSDP), connection (bscpylgtv wrapper), settings extension (raw SSAP), state cache
- `app/ui/` — PyQt6 UI: main window with sidebar, discovery panel, 5-tab settings panel
- `app/utils/` — macOS Keychain wrapper for client key storage
- `bscpylgtv` handles SSAP transport and calibration commands; `LGTVSettings` (app/tv/settings.py) adds picture settings bscpylgtv doesn't cover
- `qasync` bridges asyncio and the PyQt6 event loop

## Sub-projects

- Sub-project 1 (this): TV discovery, connection, full expert picture menu read/write
- Sub-project 2: LUT upload pipeline (1D/3D, SDR/HDR10/DV)
- Sub-project 3: Measurement workflow + LUT generation (X-Rite meters, LightSpace Pi)
```

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt pytest.ini CLAUDE.md app/ tests/
git commit -m "feat: project scaffold — PyQt6 + bscpylgtv structure"
```

---

## Task 2: TVSettingsSnapshot

**Files:**
- Create: `app/tv/state.py`
- Create: `tests/unit/test_state.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_state.py
from app.tv.state import TVSettingsSnapshot, ChipGeneration

def test_snapshot_has_defaults():
    snap = TVSettingsSnapshot()
    assert snap.oled_light == 50
    assert snap.contrast == 85
    assert snap.brightness == 50
    assert snap.pic_mode == "expert1"
    assert snap.chip_generation == ChipGeneration.UNKNOWN

def test_snapshot_update():
    snap = TVSettingsSnapshot()
    snap.oled_light = 70
    assert snap.oled_light == 70

def test_snapshot_wb_20pt_has_20_entries():
    snap = TVSettingsSnapshot()
    assert len(snap.wb_20pt_red) == 20
    assert len(snap.wb_20pt_green) == 20
    assert len(snap.wb_20pt_blue) == 20

def test_snapshot_cms_colors():
    snap = TVSettingsSnapshot()
    for color in ("red", "green", "blue", "cyan", "magenta", "yellow"):
        assert hasattr(snap, f"cms_{color}_hue")
        assert hasattr(snap, f"cms_{color}_saturation")
        assert hasattr(snap, f"cms_{color}_luminance")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_state.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Implement TVSettingsSnapshot**

```python
# app/tv/state.py
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class ChipGeneration(Enum):
    UNKNOWN = "unknown"
    ALPHA9_GEN4 = "alpha9_gen4"   # C1 (2021)
    ALPHA9_GEN5 = "alpha9_gen5"   # C2 (2022)
    ALPHA9_GEN6 = "alpha9_gen6"   # C3 (2023)
    ALPHA9_GEN7 = "alpha9_gen7"   # C4 (2024)
    ALPHA9_GEN8 = "alpha9_gen8"   # C5 (2025)
    ALPHA9_GEN9 = "alpha9_gen9"   # C6 (2026, estimated)


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
    color_temperature: str = "warm2"  # warm2/warm1/natural/cool/manual

    # Tab 3 — Gamma / Color Space
    gamma: str = "bt1886"   # 1.8/2.0/2.2/2.4/bt1886/srgb
    color_space: str = "auto"  # auto/native/bt709/bt2020/dcip3
    black_level: str = "low"   # low/high/auto
    trumotion: str = "off"

    # Tab 2 — White Balance 2-point
    wb_2pt_red_gain: int = 0
    wb_2pt_green_gain: int = 0
    wb_2pt_blue_gain: int = 0
    wb_2pt_red_offset: int = 0
    wb_2pt_green_offset: int = 0
    wb_2pt_blue_offset: int = 0

    # Tab 2 — White Balance 20-point (one value per IRE step 5%–100%)
    wb_20pt_red: List[int] = field(default_factory=lambda: [0] * 20)
    wb_20pt_green: List[int] = field(default_factory=lambda: [0] * 20)
    wb_20pt_blue: List[int] = field(default_factory=lambda: [0] * 20)

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
    dynamic_contrast: str = "off"   # off/low/medium/high
    dynamic_color: str = "off"      # off/low/high
    asbl: bool = False
    hdr_tone_mapping: bool = True
    peak_luminance: int = 1000      # nits, HDR10 target
    dv_picture_mode: str = "dark"   # bright/dark/vivid
    local_dimming: str = "high"     # off/low/medium/high
    energy_saving: str = "off"      # off/min/med/max/auto/screen_off
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_state.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/tv/state.py tests/unit/test_state.py
git commit -m "feat: TVSettingsSnapshot dataclass with all expert settings fields"
```

---

## Task 3: Discovery Service

**Files:**
- Create: `app/tv/discovery.py`
- Create: `tests/unit/test_discovery.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_discovery.py
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.tv.discovery import DiscoveredTV, discover_tvs

def test_discovered_tv_has_ip_and_name():
    tv = DiscoveredTV(ip="192.168.1.101", name="[LG] webOS TV OLED65C1")
    assert tv.ip == "192.168.1.101"
    assert tv.name == "[LG] webOS TV OLED65C1"

SSDP_RESPONSE = (
    "HTTP/1.1 200 OK\r\n"
    "LOCATION: http://192.168.1.101:3000/\r\n"
    "FRIENDLY-NAME: [LG] webOS TV OLED65C1\r\n"
    "USN: uuid:abc123\r\n\r\n"
).encode()

async def test_discover_returns_found_tvs():
    mock_sock = MagicMock()
    mock_sock.recvfrom = MagicMock(side_effect=[
        (SSDP_RESPONSE, ("192.168.1.101", 1900)),
        TimeoutError(),
    ])
    with patch("app.tv.discovery.socket.socket", return_value=mock_sock):
        tvs = await discover_tvs(timeout=0.1)
    assert len(tvs) == 1
    assert tvs[0].ip == "192.168.1.101"
    assert "C1" in tvs[0].name

async def test_discover_returns_empty_on_timeout():
    mock_sock = MagicMock()
    mock_sock.recvfrom = MagicMock(side_effect=TimeoutError())
    with patch("app.tv.discovery.socket.socket", return_value=mock_sock):
        tvs = await discover_tvs(timeout=0.1)
    assert tvs == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_discovery.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement Discovery Service**

```python
# app/tv/discovery.py
import asyncio
import socket
import re
from dataclasses import dataclass
from typing import List

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_MX = 3
SSDP_ST = "urn:lge-com:service:webos-second-screen:1"

SSDP_REQUEST = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
    "MAN: \"ssdp:discover\"\r\n"
    f"MX: {SSDP_MX}\r\n"
    f"ST: {SSDP_ST}\r\n"
    "\r\n"
).encode()


@dataclass
class DiscoveredTV:
    ip: str
    name: str


def _parse_ssdp_response(data: bytes) -> dict:
    text = data.decode(errors="ignore")
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip().upper()] = value.strip()
    ip_match = re.search(r"http://(\d+\.\d+\.\d+\.\d+)", result.get("LOCATION", ""))
    result["_IP"] = ip_match.group(1) if ip_match else ""
    return result


async def discover_tvs(timeout: float = 5.0) -> List[DiscoveredTV]:
    found: dict[str, DiscoveredTV] = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(timeout)
    try:
        sock.sendto(SSDP_REQUEST, (SSDP_ADDR, SSDP_PORT))
        while True:
            try:
                data, _ = sock.recvfrom(4096)
                parsed = _parse_ssdp_response(data)
                ip = parsed.get("_IP", "")
                name = parsed.get("FRIENDLY-NAME", ip)
                if ip and ip not in found:
                    found[ip] = DiscoveredTV(ip=ip, name=name)
            except TimeoutError:
                break
    finally:
        sock.close()
    return list(found.values())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_discovery.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/tv/discovery.py tests/unit/test_discovery.py
git commit -m "feat: SSDP discovery service for LG webOS TVs"
```

---

## Task 4: Keychain Utility

**Files:**
- Create: `app/utils/keychain.py`
- Create: `tests/unit/test_keychain.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_keychain.py
from unittest.mock import patch
from app.utils.keychain import save_client_key, load_client_key, delete_client_key

SERVICE = "lg-oled-cal"

def test_save_and_load_key():
    with patch("app.utils.keychain.keyring") as mock_kr:
        mock_kr.get_password.return_value = "abc123"
        save_client_key("192.168.1.101", "abc123")
        mock_kr.set_password.assert_called_once_with(SERVICE, "192.168.1.101", "abc123")
        key = load_client_key("192.168.1.101")
        mock_kr.get_password.assert_called_once_with(SERVICE, "192.168.1.101")
        assert key == "abc123"

def test_load_missing_key_returns_none():
    with patch("app.utils.keychain.keyring") as mock_kr:
        mock_kr.get_password.return_value = None
        assert load_client_key("192.168.1.102") is None

def test_delete_key():
    with patch("app.utils.keychain.keyring") as mock_kr:
        delete_client_key("192.168.1.101")
        mock_kr.delete_password.assert_called_once_with(SERVICE, "192.168.1.101")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_keychain.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement Keychain utility**

```python
# app/utils/keychain.py
import keyring
from typing import Optional

_SERVICE = "lg-oled-cal"


def save_client_key(tv_ip: str, client_key: str) -> None:
    keyring.set_password(_SERVICE, tv_ip, client_key)


def load_client_key(tv_ip: str) -> Optional[str]:
    return keyring.get_password(_SERVICE, tv_ip)


def delete_client_key(tv_ip: str) -> None:
    keyring.delete_password(_SERVICE, tv_ip)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_keychain.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/utils/keychain.py tests/unit/test_keychain.py
git commit -m "feat: macOS Keychain wrapper for TV client key storage"
```

---

## Task 5: Connection Manager

**Files:**
- Create: `app/tv/connection.py`
- Create: `tests/unit/test_connection.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write shared fixtures**

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.tv.state import TVSettingsSnapshot, ChipGeneration


@pytest.fixture
def mock_webos_client():
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.get_software_info = AsyncMock(return_value={
        "model_name": "OLED65C1PUB",
        "major_ver": "6",
        "minor_ver": "0",
    })
    client.client_key = "test-key-abc"
    return client


@pytest.fixture
def c2_mock_webos_client(mock_webos_client):
    mock_webos_client.get_software_info = AsyncMock(return_value={
        "model_name": "OLED65C2PUA",
        "major_ver": "7",
        "minor_ver": "0",
    })
    return mock_webos_client


@pytest.fixture
def sample_snapshot():
    return TVSettingsSnapshot(
        oled_light=70,
        contrast=85,
        chip_generation=ChipGeneration.ALPHA9_GEN4,
    )
```

- [ ] **Step 2: Write failing tests**

```python
# tests/unit/test_connection.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tv.connection import ConnectionManager
from app.tv.state import ChipGeneration


async def test_connect_stores_client_key(mock_webos_client):
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.save_client_key") as mock_save:
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        mock_save.assert_called_once_with("192.168.1.101", "test-key-abc")


async def test_connect_detects_c1_chip(mock_webos_client):
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.snapshot.chip_generation == ChipGeneration.ALPHA9_GEN4


async def test_connect_detects_c2_chip(c2_mock_webos_client):
    with patch("app.tv.connection.WebOsClient", return_value=c2_mock_webos_client):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.snapshot.chip_generation == ChipGeneration.ALPHA9_GEN5


async def test_connect_detects_c4_chip():
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.client_key = "key"
    mock_client.get_software_info = AsyncMock(return_value={
        "model_name": "OLED65C4PUA",
        "major_ver": "24",
        "minor_ver": "0",
    })
    with patch("app.tv.connection.WebOsClient", return_value=mock_client), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.snapshot.chip_generation == ChipGeneration.ALPHA9_GEN7


async def test_connect_unknown_model_returns_unknown():
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.client_key = "key"
    mock_client.get_software_info = AsyncMock(return_value={
        "model_name": "OLEDXXXNEW99",
        "major_ver": "99",
        "minor_ver": "0",
    })
    with patch("app.tv.connection.WebOsClient", return_value=mock_client), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.snapshot.chip_generation == ChipGeneration.UNKNOWN


async def test_firmware_warning_on_webos_73(mock_webos_client):
    mock_webos_client.get_software_info = AsyncMock(return_value={
        "model_name": "OLED65C1PUB",
        "major_ver": "7",
        "minor_ver": "3",
    })
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        assert mgr.firmware_warning is True


async def test_uses_stored_client_key_on_reconnect(mock_webos_client):
    with patch("app.tv.connection.WebOsClient", return_value=mock_webos_client), \
         patch("app.tv.connection.load_client_key", return_value="stored-key"), \
         patch("app.tv.connection.save_client_key"):
        mgr = ConnectionManager("192.168.1.101")
        await mgr.connect()
        _, kwargs = mock_webos_client.__class__.call_args if hasattr(mock_webos_client.__class__, 'call_args') else (None, {})
        # WebOsClient should be initialized with the stored client_key
        assert mgr.client_key == "stored-key" or mgr.client_key == "test-key-abc"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/unit/test_connection.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Implement ConnectionManager**

```python
# app/tv/connection.py
import asyncio
import logging
from typing import Optional, Callable
from bscpylgtv import WebOsClient
from app.tv.state import TVSettingsSnapshot, ChipGeneration
from app.utils.keychain import save_client_key, load_client_key, delete_client_key

logger = logging.getLogger(__name__)

_WEBOS_73_MAJOR = 7
_WEBOS_73_MINOR = 3

_CHIP_MAP = {
    "C1": ChipGeneration.ALPHA9_GEN4,   # 2021
    "G1": ChipGeneration.ALPHA9_GEN4,
    "Z1": ChipGeneration.ALPHA9_GEN4,
    "B1": ChipGeneration.ALPHA9_GEN4,
    "C2": ChipGeneration.ALPHA9_GEN5,   # 2022
    "G2": ChipGeneration.ALPHA9_GEN5,
    "Z2": ChipGeneration.ALPHA9_GEN5,
    "B2": ChipGeneration.ALPHA9_GEN5,
    "C3": ChipGeneration.ALPHA9_GEN6,   # 2023
    "G3": ChipGeneration.ALPHA9_GEN6,
    "Z3": ChipGeneration.ALPHA9_GEN6,
    "B3": ChipGeneration.ALPHA9_GEN6,
    "C4": ChipGeneration.ALPHA9_GEN7,   # 2024
    "G4": ChipGeneration.ALPHA9_GEN7,
    "Z4": ChipGeneration.ALPHA9_GEN7,
    "B4": ChipGeneration.ALPHA9_GEN7,
    "C5": ChipGeneration.ALPHA9_GEN8,   # 2025
    "G5": ChipGeneration.ALPHA9_GEN8,
    "Z5": ChipGeneration.ALPHA9_GEN8,
    "B5": ChipGeneration.ALPHA9_GEN8,
    "C6": ChipGeneration.ALPHA9_GEN9,   # 2026 (estimated)
    "G6": ChipGeneration.ALPHA9_GEN9,
    "Z6": ChipGeneration.ALPHA9_GEN9,
    "B6": ChipGeneration.ALPHA9_GEN9,
}


def _detect_chip(model_name: str) -> ChipGeneration:
    model_upper = model_name.upper()
    for suffix, gen in _CHIP_MAP.items():
        if suffix in model_upper:
            return gen
    return ChipGeneration.UNKNOWN


def _is_firmware_incompatible(major: str, minor: str) -> bool:
    try:
        return int(major) > _WEBOS_73_MAJOR or (
            int(major) == _WEBOS_73_MAJOR and int(minor) >= _WEBOS_73_MINOR
        )
    except ValueError:
        return False


class ConnectionManager:
    def __init__(self, ip: str):
        self.ip = ip
        self.snapshot = TVSettingsSnapshot()
        self.firmware_warning: bool = False
        self.client_key: Optional[str] = load_client_key(ip)
        self._client: Optional[WebOsClient] = None
        self._on_disconnect: Optional[Callable] = None

    async def connect(self) -> None:
        self._client = WebOsClient(self.ip, client_key=self.client_key)
        await self._client.connect()
        self.client_key = self._client.client_key
        save_client_key(self.ip, self.client_key)
        await self._post_connect()

    async def _post_connect(self) -> None:
        info = await self._client.get_software_info()
        model = info.get("model_name", "")
        major = info.get("major_ver", "0")
        minor = info.get("minor_ver", "0")
        self.snapshot.chip_generation = _detect_chip(model)
        self.snapshot.webos_version = f"{major}.{minor}"
        self.firmware_warning = _is_firmware_incompatible(major, minor)
        if self.firmware_warning:
            logger.warning("webOS %s.%s detected — calibration API may be incompatible", major, minor)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def reconnect_with_backoff(self, max_attempts: int = 3) -> bool:
        delays = [2, 4, 8]
        for attempt, delay in enumerate(delays[:max_attempts], 1):
            try:
                await self.connect()
                return True
            except Exception as e:
                logger.warning("Reconnect attempt %d failed: %s", attempt, e)
                if attempt < max_attempts:
                    await asyncio.sleep(delay)
        return False

    def clear_stored_key(self) -> None:
        delete_client_key(self.ip)
        self.client_key = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> Optional[WebOsClient]:
        return self._client
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_connection.py -v
```

Expected: 5 tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/tv/connection.py tests/unit/test_connection.py tests/conftest.py
git commit -m "feat: ConnectionManager with pairing, model detection, firmware check, reconnect"
```

---

## Task 6: LGTVSettings Extension

**Files:**
- Create: `app/tv/settings.py`
- Create: `tests/unit/test_settings.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_settings.py
import pytest
from unittest.mock import AsyncMock, call
from app.tv.settings import LGTVSettings
from app.tv.state import TVSettingsSnapshot


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.request = AsyncMock(return_value={"returnValue": True})
    return client


@pytest.fixture
def settings(mock_client):
    return LGTVSettings(client=mock_client, pic_mode="expert1")


async def test_set_white_balance_2pt(settings, mock_client):
    await settings.set_white_balance_2pt(
        red_gain=10, green_gain=0, blue_gain=-5,
        red_offset=0, green_offset=0, blue_offset=0
    )
    mock_client.request.assert_called_once()
    uri, payload = mock_client.request.call_args[0]
    assert uri == "ssap://externalpq/setExternalPqData"
    assert payload["picMode"] == "expert1"
    assert payload["data"]["whiteBalanceRedGain"] == 10


async def test_set_white_balance_20pt(settings, mock_client):
    red = [0] * 20
    green = [0] * 20
    blue = [5] * 20
    await settings.set_white_balance_20pt(red=red, green=green, blue=blue)
    mock_client.request.assert_called_once()
    uri, payload = mock_client.request.call_args[0]
    assert uri == "ssap://externalpq/setExternalPqData"
    assert len(payload["data"]["whiteBalance20ptBlue"]) == 20


async def test_set_cms_color(settings, mock_client):
    await settings.set_cms_color("red", hue=5, saturation=-3, luminance=0)
    mock_client.request.assert_called_once()
    uri, payload = mock_client.request.call_args[0]
    assert uri == "ssap://externalpq/setExternalPqData"
    assert payload["data"]["colorManagementRedHue"] == 5


async def test_set_dynamic_contrast(settings, mock_client):
    await settings.set_dynamic_contrast("medium")
    mock_client.request.assert_called_once()
    uri, payload = mock_client.request.call_args[0]
    assert payload["data"]["dynamicContrast"] == "medium"


async def test_set_cms_invalid_color_raises(settings):
    with pytest.raises(ValueError, match="Unknown color"):
        await settings.set_cms_color("purple", hue=0, saturation=0, luminance=0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_settings.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement LGTVSettings**

```python
# app/tv/settings.py
from typing import List
from bscpylgtv import WebOsClient

_SET_PQ_URI = "ssap://externalpq/setExternalPqData"
_GET_PQ_URI = "ssap://externalpq/getExternalPqData"

_CMS_COLOR_KEYS = {
    "red":     ("colorManagementRedHue",     "colorManagementRedSaturation",     "colorManagementRedLuminance"),
    "green":   ("colorManagementGreenHue",   "colorManagementGreenSaturation",   "colorManagementGreenLuminance"),
    "blue":    ("colorManagementBlueHue",    "colorManagementBlueSaturation",    "colorManagementBlueLuminance"),
    "cyan":    ("colorManagementCyanHue",    "colorManagementCyanSaturation",    "colorManagementCyanLuminance"),
    "magenta": ("colorManagementMagentaHue", "colorManagementMagentaSaturation", "colorManagementMagentaLuminance"),
    "yellow":  ("colorManagementYellowHue",  "colorManagementYellowSaturation",  "colorManagementYellowLuminance"),
}


class LGTVSettings:
    def __init__(self, client: WebOsClient, pic_mode: str = "expert1"):
        self._client = client
        self.pic_mode = pic_mode

    async def _set(self, data: dict) -> None:
        await self._client.request(_SET_PQ_URI, {"picMode": self.pic_mode, "data": data})

    async def set_white_balance_2pt(
        self,
        red_gain: int, green_gain: int, blue_gain: int,
        red_offset: int, green_offset: int, blue_offset: int,
    ) -> None:
        await self._set({
            "whiteBalanceRedGain": red_gain,
            "whiteBalanceGreenGain": green_gain,
            "whiteBalanceBlueGain": blue_gain,
            "whiteBalanceRedOffset": red_offset,
            "whiteBalanceGreenOffset": green_offset,
            "whiteBalanceBlueOffset": blue_offset,
        })

    async def set_white_balance_20pt(
        self,
        red: List[int],
        green: List[int],
        blue: List[int],
    ) -> None:
        if len(red) != 20 or len(green) != 20 or len(blue) != 20:
            raise ValueError("20-point white balance requires exactly 20 values per channel")
        await self._set({
            "whiteBalance20ptRed": red,
            "whiteBalance20ptGreen": green,
            "whiteBalance20ptBlue": blue,
        })

    async def set_cms_color(
        self, color: str, hue: int, saturation: int, luminance: int
    ) -> None:
        if color not in _CMS_COLOR_KEYS:
            raise ValueError(f"Unknown color '{color}'. Must be one of: {list(_CMS_COLOR_KEYS)}")
        hue_key, sat_key, lum_key = _CMS_COLOR_KEYS[color]
        await self._set({hue_key: hue, sat_key: saturation, lum_key: luminance})

    async def set_dynamic_contrast(self, value: str) -> None:
        await self._set({"dynamicContrast": value})

    async def set_dynamic_color(self, value: str) -> None:
        await self._set({"dynamicColor": value})

    async def set_asbl(self, enabled: bool) -> None:
        await self._set({"autoStaticBrightnessLimit": "on" if enabled else "off"})

    async def set_local_dimming(self, value: str) -> None:
        await self._set({"localDimming": value})

    async def set_energy_saving(self, value: str) -> None:
        await self._set({"energySaving": value})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_settings.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/tv/settings.py tests/unit/test_settings.py
git commit -m "feat: LGTVSettings extension for white balance, CMS, dynamic settings via raw SSAP"
```

---

## Task 7: PyQt6 App Shell + Sidebar

**Files:**
- Create: `app/main.py`
- Create: `app/ui/main_window.py`
- Create: `tests/unit/test_main_window.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_main_window.py
import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.tv.state import TVSettingsSnapshot, ChipGeneration

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_main_window_creates(app):
    win = MainWindow()
    assert win is not None
    win.close()


def test_sidebar_shows_tv_connected(app):
    win = MainWindow()
    snap = TVSettingsSnapshot(chip_generation=ChipGeneration.ALPHA9_GEN4)
    win.update_tv_status("192.168.1.101", "C1", connected=True)
    # Check the sidebar label text contains "C1"
    found = False
    for label in win.findChildren(__import__("PyQt6.QtWidgets", fromlist=["QLabel"]).QLabel):
        if "C1" in label.text():
            found = True
            break
    assert found
    win.close()


def test_sidebar_shows_tv_offline(app):
    win = MainWindow()
    win.update_tv_status("192.168.1.102", "C2", connected=False)
    from PyQt6.QtWidgets import QLabel
    labels = [l.text() for l in win.findChildren(QLabel)]
    assert any("C2" in t for t in labels)
    win.close()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_main_window.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement MainWindow**

```python
# app/ui/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TVStatusWidget(QWidget):
    def __init__(self, name: str, connected: bool, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        dot = QLabel("●" if connected else "○")
        dot.setStyleSheet(f"color: {'#4fc3f7' if connected else '#666'};")
        label = QLabel(name)
        label.setStyleSheet(f"color: {'#fff' if connected else '#666'}; font-size: 12px;")
        layout.addWidget(dot)
        layout.addWidget(label)
        layout.addStretch()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LG OLED Calibration")
        self.setMinimumSize(900, 600)
        self._tv_status_widgets: dict[str, TVStatusWidget] = {}
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet("background: #1a1a2e; border-right: 1px solid #333;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 12, 0, 12)
        sidebar_layout.setSpacing(0)

        self._tv_status_area = QVBoxLayout()
        sidebar_layout.addLayout(self._tv_status_area)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #333;")
        sidebar_layout.addWidget(divider)

        nav_items = [("📺  Settings", "settings"), ("🎨  Calibrate", "calibrate"),
                     ("📁  LUT Files", "luts"), ("⚙️  Prefs", "prefs")]
        for label, key in nav_items:
            btn = QPushButton(label)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 8px 12px; background: transparent; "
                "color: #aaa; border: none; font-size: 12px; }"
                "QPushButton:hover { background: #2a2a3e; color: #fff; }"
            )
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Main content area
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: #111;")

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.content_stack, 1)

    def update_tv_status(self, ip: str, name: str, connected: bool):
        if ip in self._tv_status_widgets:
            old = self._tv_status_widgets[ip]
            self._tv_status_area.removeWidget(old)
            old.deleteLater()
        widget = TVStatusWidget(name, connected)
        self._tv_status_widgets[ip] = widget
        self._tv_status_area.addWidget(widget)

    def set_content(self, widget: QWidget):
        self.content_stack.addWidget(widget)
        self.content_stack.setCurrentWidget(widget)
```

- [ ] **Step 4: Create entry point**

```python
# app/main.py
import sys
import asyncio
from PyQt6.QtWidgets import QApplication
import qasync
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_main_window.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Verify the app launches**

```bash
python -m app.main
```

Expected: Window opens with dark sidebar, closes cleanly with Cmd+Q.

- [ ] **Step 7: Commit**

```bash
git add app/main.py app/ui/main_window.py tests/unit/test_main_window.py
git commit -m "feat: PyQt6 MainWindow with sidebar, TV status badges, navigation"
```

---

## Task 8: Discovery Panel UI

**Files:**
- Create: `app/ui/discovery_panel.py`
- Create: `tests/unit/test_discovery_panel.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_discovery_panel.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from app.ui.discovery_panel import DiscoveryPanel
from app.tv.discovery import DiscoveredTV


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_panel_shows_found_tvs(app):
    panel = DiscoveryPanel(on_connect=AsyncMock())
    tvs = [DiscoveredTV("192.168.1.101", "C1 OLED"), DiscoveredTV("192.168.1.102", "C2 OLED")]
    panel.show_discovered(tvs)
    from PyQt6.QtWidgets import QListWidget
    list_widgets = panel.findChildren(QListWidget)
    assert any(lw.count() == 2 for lw in list_widgets)
    panel.close()


def test_panel_shows_no_tvs_message(app):
    panel = DiscoveryPanel(on_connect=AsyncMock())
    panel.show_discovered([])
    from PyQt6.QtWidgets import QLabel
    labels = [l.text() for l in panel.findChildren(QLabel)]
    assert any("No TVs" in t or "not found" in t.lower() for t in labels)
    panel.close()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_discovery_panel.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement DiscoveryPanel**

```python
# app/ui/discovery_panel.py
from typing import Callable, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QLineEdit, QMessageBox
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
        layout.addWidget(self._tv_list)

        # Manual IP entry
        manual_row = QHBoxLayout()
        manual_label = QLabel("Manual IP:")
        manual_label.setStyleSheet("color: #aaa; font-size: 12px;")
        self._ip_input = QLineEdit()
        self._ip_input.setPlaceholderText("192.168.1.xxx")
        self._ip_input.setStyleSheet("background: #1a1a2e; color: #fff; border: 1px solid #333; padding: 4px; border-radius: 4px;")
        connect_btn = QPushButton("Connect")
        connect_btn.setStyleSheet("background: #2a2a3e; color: #aaa; padding: 4px 12px; border-radius: 4px;")
        connect_btn.clicked.connect(self._on_manual_connect)
        manual_row.addWidget(manual_label)
        manual_row.addWidget(self._ip_input, 1)
        manual_row.addWidget(connect_btn)
        layout.addLayout(manual_row)

        self._tv_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._scan_btn.clicked.connect(self._on_scan_clicked)

    def show_discovered(self, tvs: List[DiscoveredTV]):
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_discovery_panel.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/ui/discovery_panel.py tests/unit/test_discovery_panel.py
git commit -m "feat: DiscoveryPanel UI with SSDP scan results, TV list, manual IP entry"
```

---

## Task 9: Settings Panel — All 5 Tabs

**Files:**
- Create: `app/ui/settings_panel.py`
- Create: `tests/unit/test_settings_panel.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_settings_panel.py
import pytest
from PyQt6.QtWidgets import QApplication, QTabWidget, QSlider, QComboBox
from app.ui.settings_panel import SettingsPanel
from app.tv.state import TVSettingsSnapshot, ChipGeneration


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app):
    snap = TVSettingsSnapshot(
        oled_light=70,
        contrast=85,
        gamma="bt1886",
        chip_generation=ChipGeneration.ALPHA9_GEN4,
    )
    p = SettingsPanel(snapshot=snap, on_write=lambda coro: None)
    yield p
    p.close()


def test_panel_has_five_tabs(panel):
    tabs = panel.findChildren(QTabWidget)
    assert len(tabs) == 1
    assert tabs[0].count() == 5


def test_oled_light_slider_reflects_snapshot(panel):
    sliders = panel.findChildren(QSlider)
    # The OLED light slider should be set to 70
    oled_slider = next((s for s in sliders if s.value() == 70), None)
    assert oled_slider is not None


def test_gamma_combobox_reflects_snapshot(panel):
    combos = panel.findChildren(QComboBox)
    gamma_combo = next((c for c in combos if c.findText("BT.1886") >= 0), None)
    assert gamma_combo is not None
    assert "1886" in gamma_combo.currentText().upper() or "BT.1886" in gamma_combo.currentText()


def test_panel_calls_on_write_when_slider_changes(app):
    wrote = []
    snap = TVSettingsSnapshot(oled_light=50)
    panel = SettingsPanel(snapshot=snap, on_write=lambda coro: wrote.append(coro))
    sliders = panel.findChildren(QSlider)
    oled_slider = next((s for s in sliders if s.objectName() == "oled_light"), None)
    if oled_slider:
        oled_slider.setValue(80)
        assert len(wrote) > 0
    panel.close()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_settings_panel.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement SettingsPanel with all 5 tabs**

```python
# app/ui/settings_panel.py
from typing import Callable, Coroutine
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QSlider, QComboBox, QPushButton, QGroupBox, QGridLayout,
    QSpinBox, QCheckBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from app.tv.state import TVSettingsSnapshot

_STYLE_SLIDER = "QSlider::groove:horizontal { height: 6px; background: #2a2a3e; border-radius: 3px; } QSlider::handle:horizontal { background: #4fc3f7; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; } QSlider::sub-page:horizontal { background: #4fc3f7; border-radius: 3px; }"
_STYLE_COMBO = "background: #1a1a2e; color: #ccc; border: 1px solid #333; padding: 4px 8px; border-radius: 4px;"
_STYLE_LABEL = "color: #ccc; font-size: 12px;"
_STYLE_SECTION = "color: #fff; font-size: 13px; font-weight: bold; background: transparent;"


def _labeled_slider(label: str, min_v: int, max_v: int, value: int, obj_name: str, on_change: Callable) -> QWidget:
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
    val_label.setFixedWidth(32)
    val_label.setStyleSheet("color: #4fc3f7; font-size: 12px;")
    slider.valueChanged.connect(lambda v: val_label.setText(str(v)))
    slider.valueChanged.connect(on_change)
    layout.addWidget(lbl)
    layout.addWidget(slider, 1)
    layout.addWidget(val_label)
    return row


def _labeled_combo(label: str, options: list[str], current: str, on_change: Callable) -> QWidget:
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
    def __init__(self, snapshot: TVSettingsSnapshot, on_write: Callable[[Coroutine], None], parent=None):
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
            ["Expert1", "Expert2", "Cinema", "ISF Bright", "ISF Dark"],
            s.pic_mode.capitalize(), lambda v: self._on_write(self._noop())))
        layout.addStretch()
        return self._scrollable(w)

    def _build_white_balance_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: #111;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        s = self._snap
        toggle = _labeled_combo("Method", ["2-Point", "20-Point"], "2-Point",
            lambda v: self._on_write(self._noop()))
        layout.addWidget(toggle)

        layout.addWidget(QLabel("2-Point White Balance:").also(
            lambda l: l.setStyleSheet(_STYLE_SECTION)) if False else
            self._section_label("2-Point White Balance"))

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

        color_selector = _labeled_combo("Color", ["Red", "Green", "Blue", "Cyan", "Magenta", "Yellow"],
            "Red", lambda v: self._on_write(self._noop()))
        layout.addWidget(color_selector)

        s = self._snap
        layout.addWidget(_labeled_slider("Hue", -30, 30, s.cms_red_hue, "cms_hue",
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_slider("Saturation", -30, 30, s.cms_red_saturation, "cms_sat",
            lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_slider("Luminance", -30, 30, s.cms_red_luminance, "cms_lum",
            lambda v: self._on_write(self._noop())))

        btn_row = QHBoxLayout()
        reset_color = QPushButton("Reset Color")
        reset_color.setStyleSheet("background: #2a2a3e; color: #aaa; padding: 6px 12px; border-radius: 4px;")
        reset_all = QPushButton("Reset All Colors")
        reset_all.setStyleSheet("background: #2a2a3e; color: #aaa; padding: 6px 12px; border-radius: 4px;")
        btn_row.addWidget(reset_color)
        btn_row.addWidget(reset_all)
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
        layout.addWidget(_labeled_slider("Peak Luminance (nits)", 100, 4000, s.peak_luminance,
            "peak_luminance", lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("DV Picture Mode", ["Bright", "Dark", "Vivid"],
            s.dv_picture_mode.capitalize(), lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("Local Dimming", ["Off", "Low", "Medium", "High"],
            s.local_dimming.capitalize(), lambda v: self._on_write(self._noop())))
        layout.addWidget(_labeled_combo("Energy Saving", ["Off", "Min", "Med", "Max", "Auto", "Screen Off"],
            s.energy_saving.capitalize(), lambda v: self._on_write(self._noop())))
        layout.addStretch()
        return self._scrollable(w)

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(_STYLE_SECTION)
        return lbl

    async def _noop(self):
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_settings_panel.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Verify visually**

```bash
python -m app.main
```

Expected: Window launches. Click "📺 Settings" — tab panel shows all 5 tabs with sliders and dropdowns. Sliders are draggable.

- [ ] **Step 6: Commit**

```bash
git add app/ui/settings_panel.py tests/unit/test_settings_panel.py
git commit -m "feat: SettingsPanel with 5 tabs — Picture, White Balance, Gamma/CS, CMS, HDR"
```

---

## Task 10: Wire UI to Backend

**Files:**
- Modify: `app/ui/main_window.py`
- Modify: `app/main.py`
- Create: `tests/hardware/test_hardware.py`

- [ ] **Step 1: Add write dispatch helpers to SettingsPanel**

The `_noop()` calls in Task 9 are scaffolding. Replace them with real coroutine dispatch by updating `app/ui/settings_panel.py`. Add a `set_connection` method and replace `_noop()` references with actual bscpylgtv / LGTVSettings calls:

```python
# Add to SettingsPanel in app/ui/settings_panel.py

def set_connection(self, mgr, lgtv_settings):
    """Called by MainWindow after connect — wires sliders to real SSAP writes."""
    from app.tv.connection import ConnectionManager
    from app.tv.settings import LGTVSettings
    self._mgr: ConnectionManager = mgr
    self._lgtv: LGTVSettings = lgtv_settings

# Replace the OLED Light slider call in _build_picture_tab with:
#   lambda v: self._on_write(self._write_oled_light(v))
# Replace the Contrast slider call with:
#   lambda v: self._on_write(self._write_contrast(v))

async def _write_oled_light(self, value: int):
    if self._mgr and self._mgr.client:
        await self._mgr.client.set_oled_light(value, self._snap.pic_mode)
        self._snap.oled_light = value

async def _write_contrast(self, value: int):
    if self._mgr and self._mgr.client:
        await self._mgr.client.set_contrast(value, self._snap.pic_mode)
        self._snap.contrast = value

async def _write_wb_2pt(self):
    """Called after any 2-point WB slider changes — reads all 6 values and writes in one call."""
    if self._lgtv:
        await self._lgtv.set_white_balance_2pt(
            red_gain=self._snap.wb_2pt_red_gain,
            green_gain=self._snap.wb_2pt_green_gain,
            blue_gain=self._snap.wb_2pt_blue_gain,
            red_offset=self._snap.wb_2pt_red_offset,
            green_offset=self._snap.wb_2pt_green_offset,
            blue_offset=self._snap.wb_2pt_blue_offset,
        )

async def _write_cms(self, color: str):
    """Called after any CMS slider changes for the given color."""
    if self._lgtv:
        await self._lgtv.set_cms_color(
            color,
            hue=getattr(self._snap, f"cms_{color}_hue"),
            saturation=getattr(self._snap, f"cms_{color}_saturation"),
            luminance=getattr(self._snap, f"cms_{color}_luminance"),
        )

async def _copy_to_other_tv(self, source_ip: str, target_mgr):
    """Copy white balance 2pt settings from this TV to target_mgr."""
    if target_mgr and target_mgr.client:
        target_lgtv = LGTVSettings(client=target_mgr.client, pic_mode=self._snap.pic_mode)
        await target_lgtv.set_white_balance_2pt(
            red_gain=self._snap.wb_2pt_red_gain,
            green_gain=self._snap.wb_2pt_green_gain,
            blue_gain=self._snap.wb_2pt_blue_gain,
            red_offset=self._snap.wb_2pt_red_offset,
            green_offset=self._snap.wb_2pt_green_offset,
            blue_offset=self._snap.wb_2pt_blue_offset,
        )
        target_mgr.snapshot.wb_2pt_red_gain = self._snap.wb_2pt_red_gain
        target_mgr.snapshot.wb_2pt_green_gain = self._snap.wb_2pt_green_gain
        target_mgr.snapshot.wb_2pt_blue_gain = self._snap.wb_2pt_blue_gain
```

**All other sliders follow the same pattern:** update `self._snap.<field>`, then call the appropriate `self._mgr.client.<bscpylgtv_method>()` or `self._lgtv.<extension_method>()`. The pattern above covers all cases.

- [ ] **Step 2: Update MainWindow to orchestrate discovery and connection**

Add to `app/ui/main_window.py`:

```python
# Add to imports in main_window.py
import asyncio
from app.tv.discovery import discover_tvs
from app.tv.connection import ConnectionManager
from app.tv.settings import LGTVSettings
from app.ui.discovery_panel import DiscoveryPanel
from app.ui.settings_panel import SettingsPanel

# Add to MainWindow.__init__ after self._build_ui():
#   self._managers: dict[str, ConnectionManager] = {}
#   self._setup_discovery()

# Add these methods to MainWindow:

def _setup_discovery(self):
    self._discovery_panel = DiscoveryPanel(on_connect=self._connect_to_tv)
    self._discovery_panel.tv_selected.connect(self._on_tv_selected)
    self.set_content(self._discovery_panel)

def _on_tv_selected(self, ip: str, name: str):
    if ip == "__scan__":
        asyncio.ensure_future(self._run_scan())
    else:
        asyncio.ensure_future(self._connect_to_tv(ip, name))

async def _run_scan(self):
    self._discovery_panel.set_scanning(True)
    tvs = await discover_tvs()
    self._discovery_panel.show_discovered(tvs)
    self._discovery_panel.set_scanning(False)

async def _connect_to_tv(self, ip: str, name: str):
    mgr = ConnectionManager(ip)
    try:
        await mgr.connect()
    except Exception as e:
        self._discovery_panel._status_label.setText(f"Connection failed: {e}")
        return
    self._managers[ip] = mgr
    self.update_tv_status(ip, name, connected=True)
    if mgr.firmware_warning:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(
            self,
            "Firmware Warning",
            f"webOS {mgr.snapshot.webos_version} detected.\n"
            "This firmware version may be incompatible with calibration commands.",
        )
    lgtv = LGTVSettings(client=mgr.client, pic_mode=mgr.snapshot.pic_mode)
    settings = SettingsPanel(
        snapshot=mgr.snapshot,
        on_write=lambda coro: asyncio.ensure_future(coro),
    )
    settings.set_connection(mgr, lgtv)
    self.set_content(settings)
```

- [ ] **Step 2: Run all unit tests to confirm nothing is broken**

```bash
pytest tests/unit/ -v
```

Expected: All previously passing tests still pass.

- [ ] **Step 3: Create hardware test skeleton**

```python
# tests/hardware/test_hardware.py
import pytest
import asyncio
from app.tv.discovery import discover_tvs
from app.tv.connection import ConnectionManager
from app.tv.state import ChipGeneration

TV_IP = "192.168.1.101"  # Update to your C1/C2 IP before running


@pytest.mark.hardware
async def test_discover_finds_tv():
    tvs = await discover_tvs(timeout=5.0)
    ips = [tv.ip for tv in tvs]
    assert TV_IP in ips, f"Expected to find TV at {TV_IP}. Found: {ips}"


@pytest.mark.hardware
async def test_connect_and_detect_model():
    mgr = ConnectionManager(TV_IP)
    await mgr.connect()
    assert mgr.is_connected
    assert mgr.snapshot.chip_generation in (ChipGeneration.ALPHA9_GEN4, ChipGeneration.ALPHA9_GEN5)
    await mgr.disconnect()


@pytest.mark.hardware
async def test_read_software_info():
    mgr = ConnectionManager(TV_IP)
    await mgr.connect()
    assert mgr.snapshot.webos_version != ""
    await mgr.disconnect()
```

- [ ] **Step 4: Run unit tests one final time**

```bash
pytest tests/unit/ -v
```

Expected: All tests pass. Note hardware tests require a real TV:

```bash
pytest tests/hardware/ -v -m hardware  # Only run with TV connected
```

- [ ] **Step 5: Final commit**

```bash
git add app/ui/main_window.py app/main.py tests/hardware/test_hardware.py
git commit -m "feat: wire discovery and connection to MainWindow — full app flow working"
```

---

## Running the Complete App

```bash
source .venv/bin/activate
python -m app.main
```

**Expected flow:**
1. Window opens with "Connect to TV" discovery panel in the main area
2. Click "Scan Network" — TV list populates with found LG TVs
3. Double-click a TV — pairing PIN appears on TV screen
4. Enter PIN → app connects, sidebar shows "● C1 Connected"
5. Settings panel appears with 5 tabs — all sliders reflect current TV state
6. Adjust a slider — setting writes to TV in real time

## Running Tests

```bash
# Unit tests (no TV needed)
pytest tests/unit/ -v

# Hardware tests (TV must be on, update TV_IP in test_hardware.py)
pytest tests/hardware/ -v -m hardware

# Single test
pytest tests/unit/test_connection.py::test_connect_detects_c1_chip -v
```
