# Sub-project 3: Measurement Workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate X-Rite colorimeters/spectrophotometers via ArgyllCMS, control iTPG and PGenerator 1.6 pattern generators, automate patch measurement sequences (SDR/HDR10/DV), store CGATS results, and generate 1D/3D correction LUTs from measurements.

**Architecture:** `app/meter/` handles meter device discovery and single-patch readings via ArgyllCMS subprocess calls. `app/generator/` provides an abstract `PatternGenerator` interface with concrete implementations for LG iTPG (via bscpylgtv SSAP) and PGenerator 1.6 (via HTTP). `app/measurement/` orchestrates the generator + meter loop, defines patch sequences, and stores results as CGATS and JSON. `app/lut_gen/` produces 1D tone curves and 3D LUT arrays from measurement sessions. `app/ui/measurement_panel.py` wires everything into the Calibrate nav section.

**Tech Stack:** Python 3.11+, PyQt6, qasync, bscpylgtv, ArgyllCMS (external binary, called via subprocess), numpy, colour-science, pytest, pytest-asyncio, pytest-qt

**Prerequisites:** Sub-project 1 complete (ConnectionManager, LGTVSettings). Sub-project 2 complete (LUTUploader) for the optional "upload after measure" flow.

---

## ArgyllCMS Primer

ArgyllCMS must be installed separately. The app calls its command-line tools via `subprocess`:

- `spotread` — single spectral/colorimetric reading from a connected meter
- `dispcal -?` — list connected display measurement devices (device enumeration)

Key `spotread` flags used:
- `-d N` — use device number N (from device list)
- `-O output.txt` — write CGATS output to file (use `-` for stdout)
- `-e N` — number of readings to average
- `-Y` — high-res spectral (i1 Pro 2 only)
- `-H` — high-res mode

CGATS output format (subset we parse):
```
CGATS.17
...
NUMBER_OF_FIELDS 4
BEGIN_DATA_FORMAT
SAMPLE_ID XYZ_X XYZ_Y XYZ_Z
END_DATA_FORMAT
NUMBER_OF_SETS 1
BEGIN_DATA
1 0.9642 1.0000 0.8249
END_DATA
```

Install path varies. Common locations:
- macOS Homebrew: `/opt/homebrew/bin/spotread`
- Manual install: `/usr/local/bin/spotread`
- Use `shutil.which("spotread")` to locate at runtime.

---

## PGenerator 1.6 HTTP API

PGenerator by LightSpace runs on Raspberry Pi 4 and accepts HTTP commands to display test patches on its HDMI output. The API sends RGB values as query parameters. Verify the exact endpoint and port against your Pi installation — PGenerator 1.6 documentation or the LightSpace CMS guides in `Resources/` have the definitive API.

Assumed API (verify against your Pi):
- Base URL: `http://<pi-ip>:8080`
- Display patch: `GET /patch?r=<R>&g=<G>&b=<B>` where R, G, B are 0–255 integers
- Alternatively the path may be `/measure` or `/setPatch` — adapt if needed
- Black patch: `GET /patch?r=0&g=0&b=0`

The `PGeneratorClient` in this plan uses this assumed API and includes a `probe()` method that calls a known endpoint to verify connectivity before starting a measurement session. If the API differs, only `pgenerator.py` needs updating — the rest of the codebase depends on the abstract `PatternGenerator` interface.

---

## iTPG (Internal Test Pattern Generator)

LG OLEDs have a built-in TPG accessible via SSAP. bscpylgtv exposes:
- `start_itpg()` — enable the internal pattern generator
- `stop_itpg()` — disable the internal pattern generator
- `set_itpg_patch_window(win_h, win_v, patch_h, patch_v)` — set window and patch size
- `set_itpg_patch_color(r, g, b, ...)` — set current patch color (10-bit values, 0–1023)

Verify exact signatures:
```bash
python -c "import bscpylgtv; help(bscpylgtv.WebOsClient.start_itpg)"
python -c "import bscpylgtv; help(bscpylgtv.WebOsClient.set_itpg_patch_color)"
```

iTPG operates in the TV's native bit depth. RGB values are 10-bit (0–1023). The `iTPGGenerator` converts 8-bit (0–255) patch values to 10-bit for SSAP calls.

---

## File Map

| File | Responsibility |
|---|---|
| `app/meter/device.py` | `MeterDevice` dataclass; ArgyllCMS device enumeration via `spotread -?` |
| `app/meter/argyll.py` | `ArgyllReader` — subprocess wrapper for `spotread`; returns `XYZReading` |
| `app/generator/base.py` | `PatternGenerator` abstract base class |
| `app/generator/itpg.py` | `iTPGGenerator` — iTPG via bscpylgtv SSAP |
| `app/generator/pgenerator.py` | `PGeneratorClient` — PGenerator 1.6 HTTP API |
| `app/measurement/patches.py` | `PatchSequence` and predefined sequences (SDR grayscale, primaries, HDR10) |
| `app/measurement/session.py` | `MeasurementSession` — orchestrates generator + meter loop |
| `app/measurement/store.py` | CGATS and JSON read/write for measurement results |
| `app/lut_gen/tone_curve.py` | 1D LUT generation from grayscale measurements |
| `app/lut_gen/gamut.py` | 3D LUT generation from full patch set |
| `app/ui/measurement_panel.py` | Calibrate nav panel — device selection, sequence picker, run controls |
| `tests/unit/test_meter.py` | ArgyllReader unit tests (mocked subprocess) |
| `tests/unit/test_generator_itpg.py` | iTPG unit tests (mocked bscpylgtv) |
| `tests/unit/test_generator_pgenerator.py` | PGenerator unit tests (mocked HTTP) |
| `tests/unit/test_patches.py` | PatchSequence unit tests |
| `tests/unit/test_session.py` | MeasurementSession unit tests (mocked generator + meter) |
| `tests/unit/test_store.py` | CGATS/JSON storage unit tests |
| `tests/unit/test_lut_gen.py` | LUT generation unit tests (synthetic measurements) |
| `tests/unit/test_measurement_panel.py` | UI panel tests |
| `tests/hardware/test_meter_hardware.py` | Real meter integration tests |
| `tests/hardware/test_generator_hardware.py` | Real pattern generator integration tests |
| `tests/fixtures/sample_cgats.txt` | Sample CGATS measurement output |

---

## Task 1: Measurement Data Models

**Files:**
- Create: `app/meter/__init__.py`
- Create: `app/generator/__init__.py`
- Create: `app/measurement/__init__.py`
- Create: `app/lut_gen/__init__.py`
- Create: `app/meter/device.py`

- [ ] **Step 1: Create package __init__.py files**

```bash
touch app/meter/__init__.py app/generator/__init__.py \
      app/measurement/__init__.py app/lut_gen/__init__.py
```

- [ ] **Step 2: Write failing tests for MeterDevice**

```python
# tests/unit/test_meter.py  (first portion — device model)
from app.meter.device import MeterDevice, MeterType

def test_meter_device_has_name_and_type():
    d = MeterDevice(index=0, name="i1 Display Pro", meter_type=MeterType.COLORIMETER)
    assert d.index == 0
    assert d.name == "i1 Display Pro"
    assert d.meter_type == MeterType.COLORIMETER

def test_meter_type_enum():
    assert MeterType.COLORIMETER != MeterType.SPECTROPHOTOMETER
```

- [ ] **Step 3: Run to verify they fail**

```bash
pytest tests/unit/test_meter.py::test_meter_device_has_name_and_type \
       tests/unit/test_meter.py::test_meter_type_enum -v
```

Expected: `ImportError`

- [ ] **Step 4: Implement MeterDevice**

```python
# app/meter/device.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class MeterType(Enum):
    COLORIMETER = "colorimeter"
    SPECTROPHOTOMETER = "spectrophotometer"
    UNKNOWN = "unknown"


@dataclass
class MeterDevice:
    index: int
    name: str
    meter_type: MeterType = MeterType.UNKNOWN


@dataclass
class XYZReading:
    """A single colorimetric reading in CIE XYZ."""
    X: float
    Y: float
    Z: float

    @property
    def xyY(self) -> tuple[float, float, float]:
        total = self.X + self.Y + self.Z
        if total == 0:
            return (0.0, 0.0, 0.0)
        return (self.X / total, self.Y / total, self.Y)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_meter.py::test_meter_device_has_name_and_type \
       tests/unit/test_meter.py::test_meter_type_enum -v
```

Expected: 2 tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/meter/ app/generator/ app/measurement/ app/lut_gen/ tests/unit/test_meter.py
git commit -m "feat: measurement data models — MeterDevice, MeterType, XYZReading"
```

---

## Task 2: ArgyllCMS Subprocess Wrapper

**Files:**
- Create: `app/meter/argyll.py`
- Create: `tests/fixtures/sample_cgats.txt`
- Extend: `tests/unit/test_meter.py`

- [ ] **Step 1: Create CGATS fixture**

Create `tests/fixtures/sample_cgats.txt`:

```
CGATS.17
ORIGINATOR "spotread"
CREATED "Wed Apr 23 2026"
DESCRIPTOR "Spot reading"
DEVICE_CLASS "DISPLAY"
NUMBER_OF_FIELDS 4
BEGIN_DATA_FORMAT
SAMPLE_ID XYZ_X XYZ_Y XYZ_Z
END_DATA_FORMAT
NUMBER_OF_SETS 1
BEGIN_DATA
1 95.047 100.000 108.883
END_DATA
```

- [ ] **Step 2: Write failing tests for ArgyllReader**

Append to `tests/unit/test_meter.py`:

```python
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from app.meter.argyll import ArgyllReader, ArgyllNotFoundError, list_argyll_devices
from app.meter.device import MeterDevice, MeterType, XYZReading

FIXTURES = Path(__file__).parent.parent / "fixtures"

SPOTREAD_LIST_OUTPUT = b"""
spotread: Found 2 display measurement systems
 0 = 'X-Rite i1 Display Pro'
 1 = 'X-Rite i1 Pro 2'
"""

def test_list_argyll_devices_parses_output():
    with patch("app.meter.argyll.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=SPOTREAD_LIST_OUTPUT, returncode=1)
        devices = list_argyll_devices()
    assert len(devices) == 2
    assert devices[0].index == 0
    assert "i1 Display Pro" in devices[0].name
    assert devices[1].index == 1
    assert "i1 Pro 2" in devices[1].name

def test_list_argyll_devices_no_spotread_raises():
    with patch("app.meter.argyll.shutil.which", return_value=None):
        with pytest.raises(ArgyllNotFoundError):
            list_argyll_devices()

async def test_take_reading_parses_cgats():
    reader = ArgyllReader(device_index=0)
    cgats_text = (FIXTURES / "sample_cgats.txt").read_text()
    with patch("app.meter.argyll.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=cgats_text.encode(), returncode=0)
        reading = await reader.take_reading()
    assert isinstance(reading, XYZReading)
    assert abs(reading.X - 95.047) < 0.01
    assert abs(reading.Y - 100.000) < 0.01
    assert abs(reading.Z - 108.883) < 0.01

async def test_take_reading_subprocess_failure_raises():
    reader = ArgyllReader(device_index=0)
    with patch("app.meter.argyll.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=b"", returncode=2)
        with pytest.raises(RuntimeError, match="spotread failed"):
            await reader.take_reading()
```

Don't forget `import pytest` at top of test file.

- [ ] **Step 3: Run to verify they fail**

```bash
pytest tests/unit/test_meter.py -v
```

Expected: `ImportError` for `app.meter.argyll`

- [ ] **Step 4: Implement ArgyllReader**

```python
# app/meter/argyll.py
from __future__ import annotations
import asyncio
import re
import shutil
import subprocess
from typing import Optional
from app.meter.device import MeterDevice, MeterType, XYZReading


class ArgyllNotFoundError(RuntimeError):
    pass


def _spotread_path() -> str:
    path = shutil.which("spotread")
    if path is None:
        raise ArgyllNotFoundError(
            "spotread not found. Install ArgyllCMS and ensure it is in PATH.\n"
            "macOS: brew install argyllcms"
        )
    return path


def list_argyll_devices() -> list[MeterDevice]:
    """Return connected measurement devices by running spotread with no args."""
    spotread = _spotread_path()
    result = subprocess.run(
        [spotread, "-?"],
        capture_output=True,
        timeout=10,
    )
    # spotread -? exits with code 1 but prints the device list to stdout
    output = result.stdout.decode(errors="ignore")
    devices: list[MeterDevice] = []
    for line in output.splitlines():
        m = re.match(r"\s*(\d+)\s*=\s*'(.+)'", line)
        if m:
            idx = int(m.group(1))
            name = m.group(2).strip()
            meter_type = MeterType.SPECTROPHOTOMETER if "Pro 2" in name else MeterType.COLORIMETER
            devices.append(MeterDevice(index=idx, name=name, meter_type=meter_type))
    return devices


class ArgyllReader:
    def __init__(self, device_index: int = 0, avg_count: int = 3):
        self.device_index = device_index
        self.avg_count = avg_count

    async def take_reading(self) -> XYZReading:
        """Take a single averaged reading from the meter. Returns XYZ in cd/m² scale."""
        spotread = _spotread_path()
        cmd = [
            spotread,
            "-d", str(self.device_index),
            "-e", str(self.avg_count),
            "-O", "-",   # output to stdout
        ]
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, timeout=30),
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"spotread failed (code {result.returncode}): "
                f"{result.stderr.decode(errors='ignore')}"
            )
        return _parse_cgats_xyz(result.stdout.decode(errors="ignore"))


def _parse_cgats_xyz(text: str) -> XYZReading:
    """Extract the first XYZ reading from a CGATS text block."""
    in_data = False
    for line in text.splitlines():
        line = line.strip()
        if line == "BEGIN_DATA":
            in_data = True
            continue
        if line == "END_DATA":
            break
        if in_data and line:
            parts = line.split()
            if len(parts) >= 4:
                # SAMPLE_ID XYZ_X XYZ_Y XYZ_Z
                return XYZReading(X=float(parts[1]), Y=float(parts[2]), Z=float(parts[3]))
    raise ValueError("No XYZ data found in CGATS output")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_meter.py -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/meter/argyll.py tests/fixtures/sample_cgats.txt tests/unit/test_meter.py
git commit -m "feat: ArgyllReader wraps spotread for single-patch XYZ measurement"
```

---

## Task 3: Pattern Generator Abstraction + iTPG

**Files:**
- Create: `app/generator/base.py`
- Create: `app/generator/itpg.py`
- Create: `tests/unit/test_generator_itpg.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_generator_itpg.py
import pytest
from unittest.mock import AsyncMock
from app.generator.itpg import iTPGGenerator


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.start_itpg = AsyncMock(return_value={"returnValue": True})
    client.stop_itpg = AsyncMock(return_value={"returnValue": True})
    client.set_itpg_patch_color = AsyncMock(return_value={"returnValue": True})
    client.set_itpg_patch_window = AsyncMock(return_value={"returnValue": True})
    return client


@pytest.fixture
def gen(mock_client):
    return iTPGGenerator(client=mock_client)


async def test_start_calls_bscpylgtv(gen, mock_client):
    await gen.start()
    mock_client.start_itpg.assert_called_once()


async def test_stop_calls_bscpylgtv(gen, mock_client):
    await gen.stop()
    mock_client.stop_itpg.assert_called_once()


async def test_set_patch_converts_8bit_to_10bit(gen, mock_client):
    await gen.set_patch(r=128, g=64, b=255)
    mock_client.set_itpg_patch_color.assert_called_once()
    call_args = mock_client.set_itpg_patch_color.call_args
    # 128/255 * 1023 ≈ 513
    r_10bit = call_args[0][0] if call_args[0] else call_args[1].get("r")
    assert 510 <= r_10bit <= 516


async def test_set_patch_black(gen, mock_client):
    await gen.set_patch(r=0, g=0, b=0)
    mock_client.set_itpg_patch_color.assert_called_once()


async def test_set_patch_white(gen, mock_client):
    await gen.set_patch(r=255, g=255, b=255)
    call_args = mock_client.set_itpg_patch_color.call_args
    r_10bit = call_args[0][0] if call_args[0] else call_args[1].get("r")
    assert r_10bit == 1023
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/unit/test_generator_itpg.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement abstract base and iTPG**

```python
# app/generator/base.py
from abc import ABC, abstractmethod


class PatternGenerator(ABC):
    """Abstract interface for test pattern generators."""

    @abstractmethod
    async def start(self) -> None:
        """Activate the pattern generator."""

    @abstractmethod
    async def stop(self) -> None:
        """Deactivate the pattern generator and restore normal TV operation."""

    @abstractmethod
    async def set_patch(self, r: int, g: int, b: int) -> None:
        """Display a full-screen patch with the given 8-bit RGB values (0–255)."""

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_):
        await self.stop()
```

```python
# app/generator/itpg.py
from __future__ import annotations
from bscpylgtv import WebOsClient
from app.generator.base import PatternGenerator

_10BIT_MAX = 1023
_8BIT_MAX = 255


def _to_10bit(v: int) -> int:
    return round(v / _8BIT_MAX * _10BIT_MAX)


class iTPGGenerator(PatternGenerator):
    """LG internal Test Pattern Generator via bscpylgtv SSAP."""

    def __init__(self, client: WebOsClient,
                 win_h: int = 100, win_v: int = 100,
                 patch_h: int = 50, patch_v: int = 50):
        self._client = client
        self._win_h = win_h
        self._win_v = win_v
        self._patch_h = patch_h
        self._patch_v = patch_v

    async def start(self) -> None:
        await self._client.start_itpg()
        await self._client.set_itpg_patch_window(
            self._win_h, self._win_v, self._patch_h, self._patch_v
        )

    async def stop(self) -> None:
        await self._client.stop_itpg()

    async def set_patch(self, r: int, g: int, b: int) -> None:
        await self._client.set_itpg_patch_color(
            _to_10bit(r), _to_10bit(g), _to_10bit(b)
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_generator_itpg.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/generator/base.py app/generator/itpg.py tests/unit/test_generator_itpg.py
git commit -m "feat: PatternGenerator base class and iTPGGenerator via bscpylgtv"
```

---

## Task 4: PGenerator 1.6 HTTP Client

**Files:**
- Create: `app/generator/pgenerator.py`
- Create: `tests/unit/test_generator_pgenerator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_generator_pgenerator.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.generator.pgenerator import PGeneratorClient


@pytest.fixture
def gen():
    return PGeneratorClient(host="192.168.1.200", port=8080)


async def test_set_patch_sends_http_get(gen):
    with patch("app.generator.pgenerator.aiohttp.ClientSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session.get.return_value.__aenter__.return_value = mock_response

        await gen.set_patch(r=128, g=64, b=255)

        mock_session.get.assert_called_once()
        call_url = mock_session.get.call_args[0][0]
        assert "r=128" in call_url or "128" in call_url
        assert "g=64" in call_url or "64" in call_url
        assert "b=255" in call_url or "255" in call_url


async def test_probe_returns_true_on_200(gen):
    with patch("app.generator.pgenerator.aiohttp.ClientSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session.get.return_value.__aenter__.return_value = mock_response

        result = await gen.probe()
        assert result is True


async def test_probe_returns_false_on_connection_error(gen):
    import aiohttp
    with patch("app.generator.pgenerator.aiohttp.ClientSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session.get.side_effect = aiohttp.ClientError()

        result = await gen.probe()
        assert result is False


async def test_start_and_stop_are_noops(gen):
    await gen.start()   # should not raise
    await gen.stop()    # should not raise
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/unit/test_generator_pgenerator.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Add aiohttp to requirements**

Add to `requirements.txt`:
```
aiohttp>=3.9.0
```

Install:
```bash
pip install aiohttp
```

- [ ] **Step 4: Implement PGeneratorClient**

```python
# app/generator/pgenerator.py
from __future__ import annotations
import aiohttp
from app.generator.base import PatternGenerator

# Adjust _PATCH_PATH if your PGenerator installation uses a different endpoint.
# Check PGenerator 1.6 docs or verify by opening http://<pi-ip>:<port>/ in a browser.
_PATCH_PATH = "/patch"


class PGeneratorClient(PatternGenerator):
    """PGenerator 1.6 HTTP API client for Raspberry Pi 4."""

    def __init__(self, host: str, port: int = 8080):
        self.host = host
        self.port = port
        self._base_url = f"http://{host}:{port}"

    async def start(self) -> None:
        pass  # PGenerator is always running; no explicit start needed

    async def stop(self) -> None:
        await self.set_patch(0, 0, 0)  # Show black on stop

    async def set_patch(self, r: int, g: int, b: int) -> None:
        """Send HTTP GET to display an 8-bit RGB patch."""
        url = f"{self._base_url}{_PATCH_PATH}?r={r}&g={g}&b={b}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(
                        f"PGenerator HTTP error {resp.status} for patch ({r},{g},{b}): {text}"
                    )

    async def probe(self) -> bool:
        """Return True if PGenerator is reachable."""
        try:
            url = f"{self._base_url}{_PATCH_PATH}?r=0&g=0&b=0"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    return resp.status < 400
        except aiohttp.ClientError:
            return False
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_generator_pgenerator.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/generator/pgenerator.py tests/unit/test_generator_pgenerator.py requirements.txt
git commit -m "feat: PGeneratorClient — PGenerator 1.6 HTTP API for Raspberry Pi 4"
```

---

## Task 5: Patch Sequences

**Files:**
- Create: `app/measurement/patches.py`
- Create: `tests/unit/test_patches.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_patches.py
from app.measurement.patches import (
    Patch, PatchSequence,
    SDR_GRAYSCALE_21, SDR_PRIMARIES, SDR_SECONDARIES, HDR10_GRAYSCALE,
    build_sdr_full, build_hdr10_full,
)


def test_patch_has_rgb():
    p = Patch(r=128, g=0, b=0, label="50% Red")
    assert p.r == 128 and p.g == 0 and p.b == 0
    assert p.label == "50% Red"


def test_sdr_grayscale_21_has_21_patches():
    assert len(SDR_GRAYSCALE_21) == 21
    # First patch is black (0,0,0)
    assert SDR_GRAYSCALE_21[0].r == 0
    assert SDR_GRAYSCALE_21[0].g == 0
    assert SDR_GRAYSCALE_21[0].b == 0
    # Last patch is white (255,255,255)
    assert SDR_GRAYSCALE_21[-1].r == 255


def test_sdr_primaries_has_6_patches():
    assert len(SDR_PRIMARIES) == 6  # R, G, B, C, M, Y at 100%


def test_build_sdr_full_concatenates_sequences():
    seq = build_sdr_full()
    assert isinstance(seq, PatchSequence)
    assert len(seq.patches) >= 21 + 6 + 3  # grayscale + primaries + secondaries minimum


def test_hdr10_grayscale_patches_labeled():
    for p in HDR10_GRAYSCALE:
        assert p.label != ""
        assert "nit" in p.label.lower() or "%" in p.label
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/unit/test_patches.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement patch sequences**

```python
# app/measurement/patches.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class Patch:
    r: int   # 0–255
    g: int
    b: int
    label: str = ""
    is_hdr: bool = False
    nits: float = 0.0  # target luminance for HDR patches


@dataclass
class PatchSequence:
    name: str
    patches: List[Patch] = field(default_factory=list)

    def __len__(self):
        return len(self.patches)

    def __iter__(self):
        return iter(self.patches)


def _gray(pct: float) -> Patch:
    """Create a grayscale patch from 0–100% stimulus."""
    v = round(pct / 100 * 255)
    return Patch(r=v, g=v, b=v, label=f"{pct:.0f}%")


def _hdr_gray(nits: float, peak_nits: float = 1000.0) -> Patch:
    """Approximate 8-bit code for an HDR10 luminance target (for iTPG SDR-driving)."""
    pq_linear = nits / peak_nits
    # Use PQ EOTF inverse to get 10-bit code, then scale to 8-bit
    # Simplified: use linear mapping for the patch driver (actual HDR on TV side)
    v = round(pq_linear ** (1 / 2.4) * 255)
    v = max(0, min(255, v))
    return Patch(r=v, g=v, b=v, label=f"{nits:.0f} nits", is_hdr=True, nits=nits)


# SDR 21-point grayscale: 0%, 5%, 10%, ..., 100%
SDR_GRAYSCALE_21: list[Patch] = [_gray(i * 5) for i in range(21)]

# Primary and secondary colors at 100% stimulus
SDR_PRIMARIES: list[Patch] = [
    Patch(255, 0,   0,   "Red 100%"),
    Patch(0,   255, 0,   "Green 100%"),
    Patch(0,   0,   255, "Blue 100%"),
    Patch(0,   255, 255, "Cyan 100%"),
    Patch(255, 0,   255, "Magenta 100%"),
    Patch(255, 255, 0,   "Yellow 100%"),
]

SDR_SECONDARIES: list[Patch] = [
    Patch(128, 0,   0,   "Red 50%"),
    Patch(0,   128, 0,   "Green 50%"),
    Patch(0,   0,   128, "Blue 50%"),
]

# HDR10 grayscale: key luminance targets
HDR10_GRAYSCALE: list[Patch] = [
    _hdr_gray(0),
    _hdr_gray(1),
    _hdr_gray(2),
    _hdr_gray(5),
    _hdr_gray(10),
    _hdr_gray(20),
    _hdr_gray(50),
    _hdr_gray(100),
    _hdr_gray(200),
    _hdr_gray(400),
    _hdr_gray(600),
    _hdr_gray(800),
    _hdr_gray(1000),
]


def build_sdr_full() -> PatchSequence:
    """Full SDR measurement sequence: grayscale + primaries + secondaries."""
    patches = list(SDR_GRAYSCALE_21) + list(SDR_PRIMARIES) + list(SDR_SECONDARIES)
    return PatchSequence(name="SDR Full", patches=patches)


def build_hdr10_full() -> PatchSequence:
    """HDR10 sequence: grayscale + primaries."""
    patches = list(HDR10_GRAYSCALE) + list(SDR_PRIMARIES)
    return PatchSequence(name="HDR10 Full", patches=patches)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_patches.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/measurement/patches.py tests/unit/test_patches.py
git commit -m "feat: patch sequences — SDR 21pt grayscale, primaries, HDR10 grayscale"
```

---

## Task 6: Measurement Session

**Files:**
- Create: `app/measurement/session.py`
- Create: `tests/unit/test_session.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_session.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.measurement.session import MeasurementSession, PatchResult
from app.measurement.patches import Patch, PatchSequence
from app.meter.device import XYZReading


@pytest.fixture
def mock_generator():
    gen = AsyncMock()
    gen.start = AsyncMock()
    gen.stop = AsyncMock()
    gen.set_patch = AsyncMock()
    return gen


@pytest.fixture
def mock_reader():
    reader = AsyncMock()
    reader.take_reading = AsyncMock(return_value=XYZReading(X=95.0, Y=100.0, Z=108.9))
    return reader


@pytest.fixture
def two_patch_seq():
    return PatchSequence("Test", [
        Patch(0, 0, 0, "Black"),
        Patch(255, 255, 255, "White"),
    ])


async def test_session_calls_generator_for_each_patch(
    mock_generator, mock_reader, two_patch_seq
):
    session = MeasurementSession(
        generator=mock_generator, reader=mock_reader, sequence=two_patch_seq
    )
    results = await session.run()
    assert mock_generator.set_patch.call_count == 2


async def test_session_returns_patch_results(
    mock_generator, mock_reader, two_patch_seq
):
    session = MeasurementSession(
        generator=mock_generator, reader=mock_reader, sequence=two_patch_seq
    )
    results = await session.run()
    assert len(results) == 2
    assert isinstance(results[0], PatchResult)
    assert results[0].patch.label == "Black"
    assert results[0].reading.Y == 100.0


async def test_session_calls_start_and_stop(
    mock_generator, mock_reader, two_patch_seq
):
    session = MeasurementSession(
        generator=mock_generator, reader=mock_reader, sequence=two_patch_seq
    )
    await session.run()
    mock_generator.start.assert_called_once()
    mock_generator.stop.assert_called_once()


async def test_session_stop_called_even_on_error(mock_generator, mock_reader, two_patch_seq):
    mock_reader.take_reading = AsyncMock(side_effect=RuntimeError("meter disconnected"))
    session = MeasurementSession(
        generator=mock_generator, reader=mock_reader, sequence=two_patch_seq
    )
    with pytest.raises(RuntimeError, match="meter disconnected"):
        await session.run()
    mock_generator.stop.assert_called_once()


async def test_session_progress_callback_called(mock_generator, mock_reader, two_patch_seq):
    progress_calls = []
    session = MeasurementSession(
        generator=mock_generator, reader=mock_reader, sequence=two_patch_seq,
        on_progress=lambda i, total, result: progress_calls.append((i, total))
    )
    await session.run()
    assert progress_calls == [(1, 2), (2, 2)]
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/unit/test_session.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement MeasurementSession**

```python
# app/measurement/session.py
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Callable, List, Optional
from app.generator.base import PatternGenerator
from app.meter.argyll import ArgyllReader
from app.meter.device import XYZReading
from app.measurement.patches import Patch, PatchSequence

_SETTLE_SECONDS = 0.5  # Pause after setting patch before reading — adjust for your setup


@dataclass
class PatchResult:
    patch: Patch
    reading: XYZReading


class MeasurementSession:
    def __init__(
        self,
        generator: PatternGenerator,
        reader: ArgyllReader,
        sequence: PatchSequence,
        settle_time: float = _SETTLE_SECONDS,
        on_progress: Optional[Callable[[int, int, PatchResult], None]] = None,
    ):
        self._generator = generator
        self._reader = reader
        self._sequence = sequence
        self._settle_time = settle_time
        self._on_progress = on_progress

    async def run(self) -> List[PatchResult]:
        results: List[PatchResult] = []
        total = len(self._sequence)
        await self._generator.start()
        try:
            for i, patch in enumerate(self._sequence, start=1):
                await self._generator.set_patch(patch.r, patch.g, patch.b)
                await asyncio.sleep(self._settle_time)
                reading = await self._reader.take_reading()
                result = PatchResult(patch=patch, reading=reading)
                results.append(result)
                if self._on_progress:
                    self._on_progress(i, total, result)
        finally:
            await self._generator.stop()
        return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_session.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/measurement/session.py tests/unit/test_session.py
git commit -m "feat: MeasurementSession orchestrates generator+meter loop with progress callback"
```

---

## Task 7: CGATS + JSON Storage

**Files:**
- Create: `app/measurement/store.py`
- Create: `tests/unit/test_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_store.py
import json
import pytest
from pathlib import Path
from app.measurement.store import save_cgats, load_cgats, save_json, load_json
from app.measurement.session import PatchResult
from app.measurement.patches import Patch
from app.meter.device import XYZReading


@pytest.fixture
def sample_results():
    return [
        PatchResult(patch=Patch(0, 0, 0, "Black"), reading=XYZReading(0.0, 0.0, 0.0)),
        PatchResult(patch=Patch(255, 255, 255, "White"), reading=XYZReading(95.0, 100.0, 108.9)),
    ]


def test_save_and_load_cgats(tmp_path, sample_results):
    path = tmp_path / "results.cgats"
    save_cgats(sample_results, path)
    assert path.exists()
    loaded = load_cgats(path)
    assert len(loaded) == 2
    assert abs(loaded[1].reading.Y - 100.0) < 0.01


def test_cgats_format_has_required_headers(tmp_path, sample_results):
    path = tmp_path / "results.cgats"
    save_cgats(sample_results, path)
    text = path.read_text()
    assert "CGATS" in text
    assert "XYZ_X" in text
    assert "BEGIN_DATA" in text
    assert "END_DATA" in text


def test_save_and_load_json(tmp_path, sample_results):
    path = tmp_path / "results.json"
    save_json(sample_results, path)
    assert path.exists()
    loaded = load_json(path)
    assert len(loaded) == 2
    assert loaded[0].patch.label == "Black"
    assert abs(loaded[1].reading.X - 95.0) < 0.01
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/unit/test_store.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement storage module**

```python
# app/measurement/store.py
from __future__ import annotations
import json
from pathlib import Path
from typing import List
from app.measurement.session import PatchResult
from app.measurement.patches import Patch
from app.meter.device import XYZReading


def save_cgats(results: List[PatchResult], path: Path) -> None:
    path = Path(path)
    lines = [
        "CGATS.17",
        'ORIGINATOR "lg-oled-cal"',
        "NUMBER_OF_FIELDS 7",
        "BEGIN_DATA_FORMAT",
        "SAMPLE_ID SAMPLE_NAME RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z",
        "END_DATA_FORMAT",
        f"NUMBER_OF_SETS {len(results)}",
        "BEGIN_DATA",
    ]
    for i, r in enumerate(results, start=1):
        lines.append(
            f"{i} {r.patch.label or str(i)} "
            f"{r.patch.r} {r.patch.g} {r.patch.b} "
            f"{r.reading.X:.6f} {r.reading.Y:.6f} {r.reading.Z:.6f}"
        )
    lines.append("END_DATA")
    path.write_text("\n".join(lines))


def load_cgats(path: Path) -> List[PatchResult]:
    path = Path(path)
    results: List[PatchResult] = []
    in_data = False
    for line in path.read_text().splitlines():
        line = line.strip()
        if line == "BEGIN_DATA":
            in_data = True
            continue
        if line == "END_DATA":
            break
        if in_data and line:
            parts = line.split()
            if len(parts) >= 8:
                label = parts[1]
                r, g, b = int(parts[2]), int(parts[3]), int(parts[4])
                X, Y, Z = float(parts[5]), float(parts[6]), float(parts[7])
                results.append(PatchResult(
                    patch=Patch(r=r, g=g, b=b, label=label),
                    reading=XYZReading(X=X, Y=Y, Z=Z),
                ))
    return results


def save_json(results: List[PatchResult], path: Path) -> None:
    data = [
        {
            "patch": {"r": r.patch.r, "g": r.patch.g, "b": r.patch.b,
                      "label": r.patch.label},
            "xyz": {"X": r.reading.X, "Y": r.reading.Y, "Z": r.reading.Z},
        }
        for r in results
    ]
    Path(path).write_text(json.dumps(data, indent=2))


def load_json(path: Path) -> List[PatchResult]:
    data = json.loads(Path(path).read_text())
    return [
        PatchResult(
            patch=Patch(r=d["patch"]["r"], g=d["patch"]["g"], b=d["patch"]["b"],
                        label=d["patch"]["label"]),
            reading=XYZReading(X=d["xyz"]["X"], Y=d["xyz"]["Y"], Z=d["xyz"]["Z"]),
        )
        for d in data
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_store.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/measurement/store.py tests/unit/test_store.py
git commit -m "feat: CGATS and JSON storage for measurement results"
```

---

## Task 8: LUT Generation from Measurements

**Files:**
- Create: `app/lut_gen/tone_curve.py`
- Create: `app/lut_gen/gamut.py`
- Create: `tests/unit/test_lut_gen.py`
- Add to `requirements.txt`: `colour-science>=0.4.4`

- [ ] **Step 1: Add colour-science dependency**

Append to `requirements.txt`:
```
colour-science>=0.4.4
numpy>=1.26.0
```

Install:
```bash
pip install colour-science numpy
```

- [ ] **Step 2: Write failing tests**

```python
# tests/unit/test_lut_gen.py
import numpy as np
import pytest
from app.measurement.session import PatchResult
from app.measurement.patches import Patch, SDR_GRAYSCALE_21
from app.meter.device import XYZReading
from app.lut_gen.tone_curve import generate_1d_lut_from_grayscale
from app.lut_gen.gamut import generate_3d_lut_from_measurements
from app.tv.lut import LUT1D, LUT3D


def _make_linear_grayscale_results() -> list[PatchResult]:
    """Synthetic measurements: Y rises linearly with code value."""
    results = []
    for patch in SDR_GRAYSCALE_21:
        stim = patch.r / 255
        Y = stim * 100.0  # linear response
        results.append(PatchResult(patch=patch, reading=XYZReading(X=Y * 0.95, Y=Y, Z=Y * 1.09)))
    return results


def test_generate_1d_lut_returns_lut1d():
    results = _make_linear_grayscale_results()
    lut = generate_1d_lut_from_grayscale(results, target_gamma=2.4)
    assert isinstance(lut, LUT1D)
    assert lut.data.shape == (3, 1024)


def test_generate_1d_lut_identity_for_perfect_display():
    """A display with perfect gamma 2.4 should produce an identity LUT."""
    results = []
    for patch in SDR_GRAYSCALE_21:
        stim = patch.r / 255
        # Perfect 2.4 gamma response
        Y = (stim ** 2.4) * 100.0 if stim > 0 else 0.0
        results.append(PatchResult(patch=patch, reading=XYZReading(X=Y * 0.95, Y=Y, Z=Y * 1.09)))
    lut = generate_1d_lut_from_grayscale(results, target_gamma=2.4)
    # Near-identity: midpoint output should be close to 0.5
    midpoint = lut.data[0, 512]
    assert 0.4 < midpoint < 0.6


def test_generate_3d_lut_returns_lut3d():
    from app.measurement.patches import build_sdr_full
    full_seq = build_sdr_full()
    # Synthetic results: identity (output = input)
    results = []
    for patch in full_seq:
        X = patch.r / 255 * 95.047
        Y = patch.g / 255 * 100.0
        Z = patch.b / 255 * 108.883
        results.append(PatchResult(patch=patch, reading=XYZReading(X=X, Y=Y, Z=Z)))
    lut = generate_3d_lut_from_measurements(results, lut_size=17)
    assert isinstance(lut, LUT3D)
    assert lut.size == 17
    assert lut.data.shape == (17, 17, 17, 3)
```

- [ ] **Step 3: Run to verify they fail**

```bash
pytest tests/unit/test_lut_gen.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Implement tone curve generation**

```python
# app/lut_gen/tone_curve.py
from __future__ import annotations
import numpy as np
from typing import List
from app.measurement.session import PatchResult
from app.tv.lut import LUT1D


def generate_1d_lut_from_grayscale(
    results: List[PatchResult],
    target_gamma: float = 2.4,
    lut_size: int = 1024,
) -> LUT1D:
    """
    Generate a 1D correction LUT from grayscale measurements.

    Takes measured Y values and computes the correction curve needed to hit
    target_gamma (e.g., 2.4 for BT.1886-approximate) at 100 cd/m² white.

    The correction curve at each input code:
      corrected_output = (target_Y / measured_Y) ^ gamma_correction
    """
    # Extract stimulus (normalized 0–1) and measured Y (normalized to white)
    stimulus = np.array([r.patch.r / 255.0 for r in results])
    y_vals = np.array([r.reading.Y for r in results])

    # Normalize Y to white point
    white_Y = max(y_vals)
    if white_Y == 0:
        raise ValueError("White point Y is zero — check measurement data")
    y_norm = y_vals / white_Y

    # Target: ideal gamma 2.4 response
    eps = 1e-6
    y_target = np.where(stimulus > 0, stimulus ** target_gamma, 0.0)

    # Compute per-sample correction ratio (clamped to avoid div/0)
    y_norm_safe = np.where(y_norm > eps, y_norm, eps)
    correction_ratio = np.where(y_target > eps, y_target / y_norm_safe, 1.0)

    # Build 1024-point LUT by interpolating the correction curve
    x_lut = np.linspace(0, 1, lut_size)
    correction_interp = np.interp(x_lut, stimulus, correction_ratio)

    # Apply correction to produce output values
    lut_out = np.clip(x_lut * correction_interp, 0, 1).astype(np.float32)

    # Same correction for R, G, B (1D LUT is neutral axis only)
    data = np.stack([lut_out, lut_out, lut_out], axis=0)
    return LUT1D(data=data)
```

- [ ] **Step 5: Implement 3D LUT generation**

```python
# app/lut_gen/gamut.py
from __future__ import annotations
import numpy as np
from typing import List
from app.measurement.session import PatchResult
from app.tv.lut import LUT3D

try:
    import colour
    _COLOUR_AVAILABLE = True
except ImportError:
    _COLOUR_AVAILABLE = False


def generate_3d_lut_from_measurements(
    results: List[PatchResult],
    lut_size: int = 17,
    target_colorspace: str = "ITU-R BT.709",
) -> LUT3D:
    """
    Generate a 3D correction LUT from a full patch set.

    Uses thin-plate spline interpolation (via scipy) to build a correction
    volume from the measured vs. target RGB values. Requires at least
    grayscale + primary + secondary patches (30+ measurements).

    target_colorspace: "ITU-R BT.709" or "ITU-R BT.2020"

    Note: This is a first-order approximation. For professional results,
    use DisplayCAL's 3D LUT generation or LightSpace CMS with this
    measurement data as input.
    """
    from scipy.interpolate import RBFInterpolator

    # Convert measured XYZ to the target color space RGB
    if not _COLOUR_AVAILABLE:
        raise ImportError("colour-science required: pip install colour-science")

    cs = colour.RGB_COLOURSPACES[target_colorspace]
    xyz_to_rgb_matrix = cs.matrix_XYZ_to_RGB

    # Build known-points: input RGB (0–1) → correction offset
    known_rgb_in = []
    known_rgb_correction = []

    white_Y = max(r.reading.Y for r in results)
    if white_Y == 0:
        raise ValueError("White point Y is zero")

    for result in results:
        stim_rgb = np.array([result.patch.r, result.patch.g, result.patch.b]) / 255.0
        xyz = np.array([result.reading.X, result.reading.Y, result.reading.Z]) / white_Y * 100.0
        # Convert measured XYZ to RGB in target color space
        measured_rgb = np.clip(xyz_to_rgb_matrix @ xyz, 0, 1)
        correction = stim_rgb - measured_rgb  # how far off is the display
        known_rgb_in.append(stim_rgb)
        known_rgb_correction.append(correction)

    known_rgb_in = np.array(known_rgb_in)
    known_rgb_correction = np.array(known_rgb_correction)

    # Fit RBF interpolator
    rbf = RBFInterpolator(known_rgb_in, known_rgb_correction, kernel="thin_plate_spline")

    # Build LUT grid
    grid_1d = np.linspace(0, 1, lut_size)
    R, G, B = np.meshgrid(grid_1d, grid_1d, grid_1d, indexing="ij")
    grid_pts = np.stack([R.ravel(), G.ravel(), B.ravel()], axis=1)

    corrections = rbf(grid_pts)
    corrected = np.clip(grid_pts + corrections, 0, 1)
    data = corrected.reshape(lut_size, lut_size, lut_size, 3).astype(np.float32)

    return LUT3D(data=data, size=lut_size)
```

- [ ] **Step 6: Add scipy to requirements.txt**

Append:
```
scipy>=1.13.0
```

Install:
```bash
pip install scipy
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/unit/test_lut_gen.py -v
```

Expected: 3 tests pass (the 3D LUT test may be slow — ~2–5 seconds for RBF fit).

- [ ] **Step 8: Commit**

```bash
git add app/lut_gen/tone_curve.py app/lut_gen/gamut.py tests/unit/test_lut_gen.py requirements.txt
git commit -m "feat: 1D tone curve and 3D LUT generation from measurement sessions"
```

---

## Task 9: Measurement Panel UI

**Files:**
- Create: `app/ui/measurement_panel.py`
- Create: `tests/unit/test_measurement_panel.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_measurement_panel.py
import pytest
from unittest.mock import AsyncMock
from PyQt6.QtWidgets import QApplication, QPushButton, QComboBox, QLabel
from app.ui.measurement_panel import MeasurementPanel
from app.meter.device import MeterDevice, MeterType


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app):
    p = MeasurementPanel(on_run=AsyncMock(), on_upload_lut=AsyncMock())
    yield p
    p.close()


def test_panel_creates(panel):
    assert panel is not None


def test_panel_has_run_button(panel):
    buttons = [b.text() for b in panel.findChildren(QPushButton)]
    assert any("measure" in t.lower() or "run" in t.lower() or "start" in t.lower() for t in buttons)


def test_panel_has_sequence_selector(panel):
    combos = panel.findChildren(QComboBox)
    assert len(combos) >= 1
    all_items = []
    for c in combos:
        for i in range(c.count()):
            all_items.append(c.itemText(i))
    assert any("SDR" in item or "sdr" in item.lower() for item in all_items)


def test_populate_meters_updates_combo(panel):
    devices = [
        MeterDevice(0, "i1 Display Pro", MeterType.COLORIMETER),
        MeterDevice(1, "i1 Pro 2", MeterType.SPECTROPHOTOMETER),
    ]
    panel.populate_meters(devices)
    combos = panel.findChildren(QComboBox)
    meter_items = []
    for c in combos:
        for i in range(c.count()):
            meter_items.append(c.itemText(i))
    assert any("i1" in item for item in meter_items)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/unit/test_measurement_panel.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement MeasurementPanel**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_measurement_panel.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/ui/measurement_panel.py tests/unit/test_measurement_panel.py
git commit -m "feat: MeasurementPanel UI — device selection, sequence picker, progress bar, log"
```

---

## Task 10: Wire Measurement Workflow into MainWindow

**Files:**
- Modify: `app/ui/main_window.py`

- [ ] **Step 1: Wire MeasurementPanel into MainWindow**

Add to imports in `app/ui/main_window.py`:

```python
import asyncio
from app.ui.measurement_panel import MeasurementPanel
from app.meter.argyll import ArgyllReader, list_argyll_devices, ArgyllNotFoundError
from app.generator.itpg import iTPGGenerator
from app.generator.pgenerator import PGeneratorClient
from app.measurement.patches import build_sdr_full, build_hdr10_full, SDR_GRAYSCALE_21, PatchSequence
from app.measurement.session import MeasurementSession
from app.measurement.store import save_cgats, save_json
from app.lut_gen.tone_curve import generate_1d_lut_from_grayscale
from app.lut_gen.gamut import generate_3d_lut_from_measurements
from app.tv.upload import LUTUploader, LUTTarget
from pathlib import Path
import datetime
```

Add `_measurement_results` and `_measurement_panel` to `MainWindow.__init__` after `self._build_ui()`:

```python
self._measurement_results = []
self._measurement_panel = MeasurementPanel(
    on_run=self._on_measurement_action,
    on_upload_lut=lambda: asyncio.ensure_future(self._upload_measurement_luts()),
)
```

Add `_on_nav` handling for "calibrate":

```python
elif key == "calibrate":
    self.set_content(self._measurement_panel)
```

Add measurement methods to MainWindow:

```python
def _on_measurement_action(self, action):
    if action == "__scan_meters__":
        asyncio.ensure_future(self._scan_meters())
    elif isinstance(action, dict) and action.get("action") == "measure":
        asyncio.ensure_future(self._run_measurement(action))

async def _scan_meters(self):
    try:
        devices = list_argyll_devices()
        self._measurement_panel.populate_meters(devices)
        self._measurement_panel.log(f"Found {len(devices)} meter(s)")
    except ArgyllNotFoundError as e:
        self._measurement_panel.log(f"ArgyllCMS not found: {e}")

async def _run_measurement(self, config: dict):
    if not self._managers:
        self._measurement_panel.log("No TV connected")
        return

    mgr = next(iter(self._managers.values()))
    if not mgr.is_connected:
        self._measurement_panel.log("TV not connected")
        return

    # Build patch sequence
    seq_name = config.get("sequence", "")
    if "HDR10" in seq_name:
        sequence = build_hdr10_full()
    else:
        sequence = build_sdr_full()

    # Build generator
    if config.get("use_itpg"):
        generator = iTPGGenerator(client=mgr.client)
    else:
        pgen_ip = config.get("pgen_ip", "192.168.1.200")
        generator = PGeneratorClient(host=pgen_ip)

    # Build reader (use first detected meter, index 0 as default)
    reader = ArgyllReader(device_index=0)

    self._measurement_panel.set_running(True)
    self._measurement_panel.log(f"Starting {sequence.name} — {len(sequence)} patches")

    def on_progress(i, total, result):
        self._measurement_panel.set_progress(i, total, result.patch.label)
        self._measurement_panel.log(
            f"  [{i}/{total}] {result.patch.label}: "
            f"X={result.reading.X:.3f} Y={result.reading.Y:.3f} Z={result.reading.Z:.3f}"
        )

    try:
        session = MeasurementSession(
            generator=generator,
            reader=reader,
            sequence=sequence,
            on_progress=on_progress,
        )
        self._measurement_results = await session.run()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = Path.home() / "Documents" / f"lg_cal_{timestamp}.cgats"
        save_cgats(self._measurement_results, save_path)
        self._measurement_panel.log(f"Saved: {save_path}")
        self._measurement_panel.enable_upload()
    except Exception as e:
        self._measurement_panel.log(f"Measurement failed: {e}")
    finally:
        self._measurement_panel.set_running(False)

async def _upload_measurement_luts(self):
    if not self._measurement_results:
        self._measurement_panel.log("No measurement data — run a measurement first")
        return
    if not self._managers:
        self._measurement_panel.log("No TV connected")
        return

    self._measurement_panel.log("Generating 1D tone curve LUT…")
    try:
        lut_1d = generate_1d_lut_from_grayscale(self._measurement_results)
        self._measurement_panel.log("Generating 3D gamut LUT…")
        lut_3d = generate_3d_lut_from_measurements(self._measurement_results, lut_size=17)
    except Exception as e:
        self._measurement_panel.log(f"LUT generation failed: {e}")
        return

    for ip, mgr in self._managers.items():
        if not mgr.is_connected:
            continue
        uploader = LUTUploader(client=mgr.client, pic_mode=mgr.snapshot.pic_mode)
        try:
            await uploader.upload_1d(lut_1d)
            self._measurement_panel.log(f"1D LUT uploaded to {ip}")
            await uploader.upload_3d(lut_3d, target=LUTTarget.BT709)
            self._measurement_panel.log(f"3D LUT uploaded to {ip}")
        except Exception as e:
            self._measurement_panel.log(f"Upload failed for {ip}: {e}")
```

- [ ] **Step 2: Run all unit tests**

```bash
pytest tests/unit/ -v
```

Expected: All tests pass.

- [ ] **Step 3: Verify the app launches and Calibrate nav works**

```bash
python -m app.main
```

Expected:
1. Window opens
2. Click "🎨 Calibrate" in sidebar — MeasurementPanel appears
3. Click "Scan Meters" — if ArgyllCMS is installed and a meter is connected, the meter dropdown populates
4. Without a meter: logs "ArgyllCMS not found" or "Found 0 meter(s)"

- [ ] **Step 4: Final commit**

```bash
git add app/ui/main_window.py
git commit -m "feat: wire MeasurementPanel into MainWindow — full calibration workflow end-to-end"
```

---

## Task 11: Hardware Integration Tests

**Files:**
- Create: `tests/hardware/test_meter_hardware.py`
- Create: `tests/hardware/test_generator_hardware.py`

- [ ] **Step 1: Create meter hardware tests**

```python
# tests/hardware/test_meter_hardware.py
import pytest
from app.meter.argyll import ArgyllReader, list_argyll_devices
from app.meter.device import XYZReading


@pytest.mark.hardware
def test_list_devices_finds_meter():
    """Requires: ArgyllCMS installed, at least one meter connected via USB."""
    devices = list_argyll_devices()
    assert len(devices) > 0, "No meters found — is a meter connected and ArgyllCMS installed?"


@pytest.mark.hardware
async def test_take_single_reading():
    """Requires: meter connected, pointing at a white surface or display."""
    reader = ArgyllReader(device_index=0, avg_count=1)
    reading = await reader.take_reading()
    assert isinstance(reading, XYZReading)
    assert reading.Y > 0, "Y value is 0 — is the meter pointing at a lit surface?"
```

- [ ] **Step 2: Create generator hardware tests**

```python
# tests/hardware/test_generator_hardware.py
import pytest
from app.generator.itpg import iTPGGenerator
from app.generator.pgenerator import PGeneratorClient
from app.tv.connection import ConnectionManager

TV_IP = "192.168.1.101"    # Update before running
PGEN_IP = "192.168.1.200"  # Update before running


@pytest.fixture
async def connected_mgr():
    mgr = ConnectionManager(TV_IP)
    await mgr.connect()
    yield mgr
    await mgr.disconnect()


@pytest.mark.hardware
async def test_itpg_displays_white_patch(connected_mgr):
    gen = iTPGGenerator(client=connected_mgr.client)
    async with gen:
        await gen.set_patch(255, 255, 255)
        # Visually verify: TV should show a white patch in the center


@pytest.mark.hardware
async def test_itpg_displays_red_patch(connected_mgr):
    gen = iTPGGenerator(client=connected_mgr.client)
    async with gen:
        await gen.set_patch(255, 0, 0)


@pytest.mark.hardware
async def test_pgenerator_probe():
    gen = PGeneratorClient(host=PGEN_IP)
    result = await gen.probe()
    assert result is True, f"PGenerator not reachable at {PGEN_IP}:8080"


@pytest.mark.hardware
async def test_pgenerator_displays_white():
    gen = PGeneratorClient(host=PGEN_IP)
    async with gen:
        await gen.set_patch(255, 255, 255)
```

- [ ] **Step 3: Run all unit tests one final time**

```bash
pytest tests/unit/ -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/hardware/test_meter_hardware.py tests/hardware/test_generator_hardware.py
git commit -m "feat: hardware integration tests for meter and pattern generator"
```

---

## Running Tests

```bash
# All unit tests (no hardware needed)
pytest tests/unit/ -v

# Hardware meter tests (USB meter + ArgyllCMS required)
pytest tests/hardware/test_meter_hardware.py -v -m hardware

# Hardware generator tests (TV + PGenerator Pi required)
pytest tests/hardware/test_generator_hardware.py -v -m hardware

# Full measurement workflow test (everything connected)
pytest tests/hardware/ -v -m hardware
```

## End-to-End Calibration Flow

```bash
source .venv/bin/activate
python -m app.main
```

1. Connect TV — sidebar shows "● C1 Connected"
2. Click "🎨 Calibrate"
3. Click "Scan Meters" — i1 Display Pro or i1 Pro 2 appears in dropdown
4. Select generator (iTPG or PGenerator IP)
5. Select sequence (SDR Full)
6. Click "Start Measurement" — TV displays patches, meter reads each one, log fills in
7. After completion — CGATS file saved to `~/Documents/lg_cal_YYYYMMDD_HHMMSS.cgats`
8. Click "Generate & Upload LUT" — 1D + 3D LUTs generated and uploaded to TV
```
