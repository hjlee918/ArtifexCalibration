# Sub-project 2: LUT Upload Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse 1D and 3D LUT files (.cube, .cal), upload them to LG OLED TVs via bscpylgtv, upload Dolby Vision configuration files, and expose a LUT management UI panel.

**Architecture:** A `LUTParser` module converts standard LUT file formats into the numpy array shapes bscpylgtv expects. A `LUTUploader` service wraps the bscpylgtv calibration upload methods, routing to the correct call based on LUT type and target picture mode. A `DolbyVisionConfig` module handles the `.txt`/`.cfg` DV config upload as a raw SSAP payload. The `LUTPanel` PyQt6 widget ties it together with a file browser and upload controls.

**Tech Stack:** Python 3.11+, PyQt6, bscpylgtv, numpy, pytest, pytest-asyncio, pytest-qt

**Prerequisites:** Sub-project 1 must be complete (ConnectionManager, TVSettingsSnapshot, LGTVSettings available).

---

## bscpylgtv Upload API Reference

Before implementing, verify these method signatures in the installed bscpylgtv version:

```bash
python -c "import bscpylgtv; help(bscpylgtv.WebOsClient.upload_1d_lut)"
python -c "import bscpylgtv; help(bscpylgtv.WebOsClient.upload_3by3_gamut_data)"
python -c "import bscpylgtv; help(bscpylgtv.WebOsClient.upload_3d_lut_bt709)"
python -c "import bscpylgtv; help(bscpylgtv.WebOsClient.upload_3d_lut_bt2020)"
```

Expected shapes (from bscpylgtv source):
- **1D LUT:** numpy array shape `(3, 1024)` — rows are R, G, B; values in range `[0, 1]`
- **3x3 gamut matrix:** numpy array shape `(3, 3)` — row-major, values are float coefficients
- **3D LUT (BT.709/BT.2020):** numpy array shape `(N, N, N, 3)` where N is typically 17 or 33 — last axis is RGB output; input domain `[0, 1]`, output domain `[0, 1]`

If bscpylgtv uses different shapes, adapt the `LUTParser` output accordingly.

---

## File Map

| File | Responsibility |
|---|---|
| `app/tv/lut.py` | `LUT1D`, `LUT3D` dataclasses; `.cube` parser; `.cal` parser |
| `app/tv/upload.py` | `LUTUploader` — wraps bscpylgtv upload methods, handles SDR/HDR10/DV routing |
| `app/tv/dv_config.py` | `DolbyVisionConfig` — load and upload `.txt`/`.cfg` DV config files |
| `app/ui/lut_panel.py` | `LUTPanel` — file browser, LUT metadata display, upload controls |
| `tests/unit/test_lut.py` | LUT parsing unit tests (no TV, no bscpylgtv) |
| `tests/unit/test_upload.py` | LUTUploader unit tests (mocked bscpylgtv client) |
| `tests/unit/test_dv_config.py` | DV config parsing unit tests |
| `tests/unit/test_lut_panel.py` | LUT panel UI tests (mocked uploader) |
| `tests/hardware/test_lut_hardware.py` | Hardware LUT upload tests (`@pytest.mark.hardware`) |
| `tests/fixtures/test_lut_17.cube` | 17³ identity 3D LUT fixture |
| `tests/fixtures/test_lut_1d.cal` | 1D LUT cal fixture |
| `tests/fixtures/test_dv_config.txt` | DV config fixture (copy from Resources/) |

---

## Task 1: LUT Data Models + .cube Parser

**Files:**
- Create: `app/tv/lut.py`
- Create: `tests/unit/test_lut.py`
- Create: `tests/fixtures/test_lut_17.cube`

- [ ] **Step 1: Create the 17³ identity .cube fixture**

Create `tests/fixtures/test_lut_17.cube`:

```
TITLE "Identity 17x17x17"
LUT_3D_SIZE 17
DOMAIN_MIN 0.0 0.0 0.0
DOMAIN_MAX 1.0 1.0 1.0
```

Then append 17³ = 4913 lines of `R G B` data. The identity LUT has output = input, so the entry at grid index (r, g, b) is `(r/16, g/16, b/16)`. Generate with:

```bash
python3 -c "
size = 17
print('TITLE \"Identity 17x17x17\"')
print('LUT_3D_SIZE 17')
print('DOMAIN_MIN 0.0 0.0 0.0')
print('DOMAIN_MAX 1.0 1.0 1.0')
for b in range(size):
    for g in range(size):
        for r in range(size):
            print(f'{r/(size-1):.6f} {g/(size-1):.6f} {b/(size-1):.6f}')
" > tests/fixtures/test_lut_17.cube
```

- [ ] **Step 2: Create the 1D .cal fixture**

Create `tests/fixtures/test_lut_1d.cal` with a minimal identity 1D LUT in ArgyllCMS `.cal` format:

```
CAL

DESCRIPTOR "Identity 1D Cal"
ORIGINATOR "test"
NUMBER_OF_FIELDS 4
BEGIN_DATA_FORMAT
TV_R TV_G TV_B TV_in
END_DATA_FORMAT
NUMBER_OF_SETS 3
BEGIN_DATA
0.000000 0.000000 0.000000 0.000000
0.500000 0.500000 0.500000 0.500000
1.000000 1.000000 1.000000 1.000000
END_DATA
```

- [ ] **Step 3: Write failing tests**

```python
# tests/unit/test_lut.py
import numpy as np
import pytest
from pathlib import Path
from app.tv.lut import LUT1D, LUT3D, parse_cube, parse_cal

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_cube_identity_17():
    lut = parse_cube(FIXTURES / "test_lut_17.cube")
    assert isinstance(lut, LUT3D)
    assert lut.size == 17
    assert lut.data.shape == (17, 17, 17, 3)
    # identity LUT: output at (8, 8, 8) should be (0.5, 0.5, 0.5)
    np.testing.assert_allclose(lut.data[8, 8, 8], [0.5, 0.5, 0.5], atol=1e-4)


def test_parse_cube_domain_clamped():
    lut = parse_cube(FIXTURES / "test_lut_17.cube")
    assert lut.domain_min == (0.0, 0.0, 0.0)
    assert lut.domain_max == (1.0, 1.0, 1.0)


def test_parse_cube_values_in_range():
    lut = parse_cube(FIXTURES / "test_lut_17.cube")
    assert lut.data.min() >= 0.0
    assert lut.data.max() <= 1.0


def test_parse_cal_identity():
    lut = parse_cal(FIXTURES / "test_lut_1d.cal")
    assert isinstance(lut, LUT1D)
    assert lut.data.shape[0] == 3   # R, G, B rows
    assert lut.data.shape[1] > 0    # at least one entry


def test_parse_cube_wrong_extension_raises():
    with pytest.raises(ValueError, match="Expected .cube"):
        parse_cube(Path("file.txt"))


def test_parse_cal_wrong_extension_raises():
    with pytest.raises(ValueError, match="Expected .cal"):
        parse_cal(Path("file.txt"))
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
pytest tests/unit/test_lut.py -v
```

Expected: `ImportError` (module does not exist yet)

- [ ] **Step 5: Implement LUT data models and parsers**

```python
# app/tv/lut.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple
import numpy as np


@dataclass
class LUT1D:
    """1D LUT: shape (3, N) — rows are R, G, B; values in [0, 1]."""
    data: np.ndarray          # shape (3, N)
    title: str = ""


@dataclass
class LUT3D:
    """3D LUT: shape (N, N, N, 3) — axes are B, G, R input; last axis is RGB output."""
    data: np.ndarray          # shape (N, N, N, 3)
    size: int = 17
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    title: str = ""


def parse_cube(path: Path) -> LUT3D:
    """Parse an Adobe .cube 3D LUT file."""
    path = Path(path)
    if path.suffix.lower() != ".cube":
        raise ValueError(f"Expected .cube file, got: {path.suffix}")

    title = ""
    size = None
    domain_min = (0.0, 0.0, 0.0)
    domain_max = (1.0, 1.0, 1.0)
    data_lines: list[str] = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("TITLE"):
                title = line.split(None, 1)[1].strip('"')
            elif line.startswith("LUT_3D_SIZE"):
                size = int(line.split()[1])
            elif line.startswith("DOMAIN_MIN"):
                parts = line.split()
                domain_min = (float(parts[1]), float(parts[2]), float(parts[3]))
            elif line.startswith("DOMAIN_MAX"):
                parts = line.split()
                domain_max = (float(parts[1]), float(parts[2]), float(parts[3]))
            else:
                data_lines.append(line)

    if size is None:
        raise ValueError(f"LUT_3D_SIZE not found in {path}")
    if len(data_lines) != size ** 3:
        raise ValueError(
            f"Expected {size**3} data lines, got {len(data_lines)} in {path}"
        )

    # .cube iterates R fastest, then G, then B
    raw = np.array([[float(v) for v in ln.split()] for ln in data_lines],
                   dtype=np.float32)
    # Reshape to (B, G, R, 3) then transpose to (R, G, B, 3) for intuitive indexing
    data = raw.reshape(size, size, size, 3).transpose(2, 1, 0, 3)

    return LUT3D(data=data, size=size, domain_min=domain_min,
                 domain_max=domain_max, title=title)


def parse_cal(path: Path) -> LUT1D:
    """Parse an ArgyllCMS .cal 1D LUT file."""
    path = Path(path)
    if path.suffix.lower() != ".cal":
        raise ValueError(f"Expected .cal file, got: {path.suffix}")

    title = ""
    in_data = False
    r_vals, g_vals, b_vals = [], [], []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DESCRIPTOR"):
                title = line.split(None, 1)[1].strip('"')
            elif line == "BEGIN_DATA":
                in_data = True
            elif line == "END_DATA":
                in_data = False
            elif in_data and line:
                parts = line.split()
                # .cal data format: TV_R TV_G TV_B TV_in (all normalized 0..1)
                r_vals.append(float(parts[0]))
                g_vals.append(float(parts[1]))
                b_vals.append(float(parts[2]))

    data = np.array([r_vals, g_vals, b_vals], dtype=np.float32)
    return LUT1D(data=data, title=title)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/unit/test_lut.py -v
```

Expected: 6 tests pass.

- [ ] **Step 7: Commit**

```bash
git add app/tv/lut.py tests/unit/test_lut.py tests/fixtures/
git commit -m "feat: LUT1D/LUT3D data models with .cube and .cal parsers"
```

---

## Task 2: LUT Uploader

**Files:**
- Create: `app/tv/upload.py`
- Create: `tests/unit/test_upload.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_upload.py
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.tv.lut import LUT1D, LUT3D
from app.tv.upload import LUTUploader, LUTTarget


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.upload_1d_lut = AsyncMock(return_value={"returnValue": True})
    client.upload_3by3_gamut_data = AsyncMock(return_value={"returnValue": True})
    client.upload_3d_lut_bt709 = AsyncMock(return_value={"returnValue": True})
    client.upload_3d_lut_bt2020 = AsyncMock(return_value={"returnValue": True})
    return client


@pytest.fixture
def uploader(mock_client):
    return LUTUploader(client=mock_client, pic_mode="expert1")


@pytest.fixture
def identity_1d():
    data = np.tile(np.linspace(0, 1, 1024, dtype=np.float32), (3, 1))
    return LUT1D(data=data)


@pytest.fixture
def identity_3d():
    size = 17
    data = np.zeros((size, size, size, 3), dtype=np.float32)
    for r in range(size):
        for g in range(size):
            for b in range(size):
                data[r, g, b] = [r / (size - 1), g / (size - 1), b / (size - 1)]
    return LUT3D(data=data, size=size)


async def test_upload_1d_lut_calls_client(uploader, mock_client, identity_1d):
    await uploader.upload_1d(identity_1d)
    mock_client.upload_1d_lut.assert_called_once()


async def test_upload_3d_lut_bt709_calls_client(uploader, mock_client, identity_3d):
    await uploader.upload_3d(identity_3d, target=LUTTarget.BT709)
    mock_client.upload_3d_lut_bt709.assert_called_once()


async def test_upload_3d_lut_bt2020_calls_client(uploader, mock_client, identity_3d):
    await uploader.upload_3d(identity_3d, target=LUTTarget.BT2020)
    mock_client.upload_3d_lut_bt2020.assert_called_once()


async def test_upload_3d_wrong_target_raises(uploader, identity_3d):
    with pytest.raises(ValueError, match="Unknown LUTTarget"):
        await uploader.upload_3d(identity_3d, target="bad_target")


async def test_upload_failure_raises(uploader, mock_client, identity_1d):
    mock_client.upload_1d_lut = AsyncMock(return_value={"returnValue": False,
                                                          "errorText": "upload failed"})
    with pytest.raises(RuntimeError, match="upload failed"):
        await uploader.upload_1d(identity_1d)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_upload.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement LUTUploader**

```python
# app/tv/upload.py
from __future__ import annotations
from enum import Enum
import numpy as np
from bscpylgtv import WebOsClient
from app.tv.lut import LUT1D, LUT3D


class LUTTarget(str, Enum):
    BT709 = "bt709"
    BT2020 = "bt2020"


class LUTUploader:
    def __init__(self, client: WebOsClient, pic_mode: str = "expert1"):
        self._client = client
        self.pic_mode = pic_mode

    async def upload_1d(self, lut: LUT1D) -> None:
        """Upload 1D LUT. bscpylgtv expects shape (3, 1024) in [0, 1]."""
        data = _ensure_1d_shape(lut.data)
        result = await self._client.upload_1d_lut(data)
        _check_result(result)

    async def upload_3d(self, lut: LUT3D, target: LUTTarget) -> None:
        """Upload 3D LUT to the specified color space slot."""
        data = lut.data.astype(np.float32)
        if target == LUTTarget.BT709:
            result = await self._client.upload_3d_lut_bt709(data)
        elif target == LUTTarget.BT2020:
            result = await self._client.upload_3d_lut_bt2020(data)
        else:
            raise ValueError(f"Unknown LUTTarget: {target!r}")
        _check_result(result)

    async def upload_gamut_matrix(self, matrix: np.ndarray) -> None:
        """Upload a 3×3 gamut correction matrix."""
        if matrix.shape != (3, 3):
            raise ValueError(f"Gamut matrix must be (3, 3), got {matrix.shape}")
        result = await self._client.upload_3by3_gamut_data(matrix.astype(np.float32))
        _check_result(result)


def _ensure_1d_shape(data: np.ndarray) -> np.ndarray:
    """Interpolate or resample 1D LUT data to shape (3, 1024)."""
    if data.shape == (3, 1024):
        return data.astype(np.float32)
    # Resample each channel to 1024 points via linear interpolation
    x_in = np.linspace(0, 1, data.shape[1])
    x_out = np.linspace(0, 1, 1024)
    out = np.zeros((3, 1024), dtype=np.float32)
    for ch in range(3):
        out[ch] = np.interp(x_out, x_in, data[ch])
    return out


def _check_result(result: dict) -> None:
    if not result.get("returnValue", False):
        error = result.get("errorText", "unknown error")
        raise RuntimeError(f"LUT upload failed: {error}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_upload.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/tv/upload.py tests/unit/test_upload.py
git commit -m "feat: LUTUploader wraps bscpylgtv upload methods for 1D/3D LUT and gamut matrix"
```

---

## Task 3: Dolby Vision Config Upload

**Files:**
- Create: `app/tv/dv_config.py`
- Create: `tests/unit/test_dv_config.py`
- Create: `tests/fixtures/test_dv_config.txt`

- [ ] **Step 1: Create the DV config fixture**

Copy the existing DV config as a test fixture:

```bash
cp "Resources/(5) - Dolby Vision CFG File/DolbyVision_UserDisplayConfiguration.txt" \
   tests/fixtures/test_dv_config.txt
```

- [ ] **Step 2: Write failing tests**

```python
# tests/unit/test_dv_config.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock
from app.tv.dv_config import DolbyVisionConfig, load_dv_config

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_load_dv_config_parses_file():
    cfg = load_dv_config(FIXTURES / "test_dv_config.txt")
    assert isinstance(cfg, DolbyVisionConfig)
    assert len(cfg.raw_text) > 0


def test_load_dv_config_wrong_extension_raises():
    with pytest.raises(ValueError, match="Expected .txt or .cfg"):
        load_dv_config(Path("file.xyz"))


async def test_upload_dv_config_sends_ssap():
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value={"returnValue": True})
    cfg = DolbyVisionConfig(raw_text="[DisplayConfiguration]\nVersion=2\n")
    await cfg.upload(mock_client)
    mock_client.request.assert_called_once()
    uri, payload = mock_client.request.call_args[0]
    assert "dolby" in uri.lower() or "externalpq" in uri.lower()


async def test_upload_dv_config_failure_raises():
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value={"returnValue": False,
                                                    "errorText": "not supported"})
    cfg = DolbyVisionConfig(raw_text="[DisplayConfiguration]\n")
    with pytest.raises(RuntimeError, match="not supported"):
        await cfg.upload(mock_client)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/unit/test_dv_config.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Implement DV config module**

```python
# app/tv/dv_config.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

# DV config is uploaded via the externalpq SSAP endpoint.
# Verify against bscpylgtv source or LightSpace documentation if this URI changes.
_DV_CONFIG_URI = "ssap://externalpq/setDolbyVisionUserDisplayConfiguration"


@dataclass
class DolbyVisionConfig:
    raw_text: str

    async def upload(self, client) -> None:
        """Upload the DV config to the TV via SSAP."""
        payload = {"data": self.raw_text}
        result = await client.request(_DV_CONFIG_URI, payload)
        if not result.get("returnValue", False):
            error = result.get("errorText", "unknown error")
            raise RuntimeError(f"DV config upload failed: {error}")


def load_dv_config(path: Path) -> DolbyVisionConfig:
    """Load a Dolby Vision user display configuration file (.txt or .cfg)."""
    path = Path(path)
    if path.suffix.lower() not in (".txt", ".cfg"):
        raise ValueError(f"Expected .txt or .cfg file, got: {path.suffix}")
    return DolbyVisionConfig(raw_text=path.read_text())
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_dv_config.py -v
```

Expected: 4 tests pass. If the DV config SSAP URI is wrong (returns False from a real TV), update `_DV_CONFIG_URI` to match the correct endpoint — check the LightSpace CMS guides in `Resources/` for the actual SSAP URI used during DV calibration.

- [ ] **Step 6: Commit**

```bash
git add app/tv/dv_config.py tests/unit/test_dv_config.py tests/fixtures/test_dv_config.txt
git commit -m "feat: DolbyVisionConfig loads and uploads DV user display configuration via SSAP"
```

---

## Task 4: LUT Panel UI

**Files:**
- Create: `app/ui/lut_panel.py`
- Create: `tests/unit/test_lut_panel.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_lut_panel.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QComboBox
from app.ui.lut_panel import LUTPanel
from app.tv.lut import LUT3D
import numpy as np


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app):
    p = LUTPanel(on_upload=AsyncMock())
    yield p
    p.close()


def test_panel_creates(panel):
    assert panel is not None


def test_panel_has_upload_button(panel):
    buttons = [b.text() for b in panel.findChildren(QPushButton)]
    assert any("upload" in t.lower() or "Upload" in t for t in buttons)


def test_panel_has_target_selector(panel):
    combos = panel.findChildren(QComboBox)
    assert len(combos) >= 1
    texts = []
    for c in combos:
        for i in range(c.count()):
            texts.append(c.itemText(i))
    assert any("BT.709" in t or "709" in t for t in texts)


def test_panel_shows_no_file_initially(panel):
    labels = [l.text() for l in panel.findChildren(QLabel)]
    assert any("no file" in t.lower() or "select" in t.lower() or "" == t for t in labels)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_lut_panel.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement LUTPanel**

```python
# app/ui/lut_panel.py
from __future__ import annotations
from typing import Callable, Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFileDialog, QGroupBox, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from app.tv.lut import LUT1D, LUT3D, parse_cube, parse_cal
from app.tv.upload import LUTTarget

_STYLE_LABEL = "color: #ccc; font-size: 12px;"
_STYLE_BTN_PRIMARY = (
    "background: #4fc3f7; color: #000; padding: 8px 16px; border-radius: 4px; font-weight: bold;"
)
_STYLE_BTN_SECONDARY = (
    "background: #2a2a3e; color: #aaa; padding: 6px 12px; border-radius: 4px;"
)
_STYLE_COMBO = (
    "background: #1a1a2e; color: #ccc; border: 1px solid #333; padding: 4px 8px; border-radius: 4px;"
)


class LUTPanel(QWidget):
    def __init__(self, on_upload: Callable, parent=None):
        super().__init__(parent)
        self._on_upload = on_upload
        self._loaded_lut: Optional[LUT1D | LUT3D] = None
        self._lut_path: Optional[Path] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("LUT Files")
        title.setStyleSheet("color: #fff; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # File selector group
        file_group = QGroupBox("LUT File")
        file_group.setStyleSheet(
            "QGroupBox { color: #aaa; font-size: 12px; border: 1px solid #333; border-radius: 4px; margin-top: 8px; }"
            "QGroupBox::title { padding: 0 4px; }"
        )
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

        # Upload options group
        options_group = QGroupBox("Upload Options")
        options_group.setStyleSheet(file_group.styleSheet())
        options_layout = QGridLayout(options_group)
        options_layout.setSpacing(10)

        options_layout.addWidget(QLabel("Color Space Target:").also(
            lambda l: l.setStyleSheet(_STYLE_LABEL)) if False else
            self._make_label("Color Space Target:"), 0, 0)
        self._target_combo = QComboBox()
        self._target_combo.setStyleSheet(_STYLE_COMBO)
        self._target_combo.addItems(["BT.709 (SDR)", "BT.2020 (HDR10 / HLG)"])
        options_layout.addWidget(self._target_combo, 0, 1)

        options_layout.addWidget(self._make_label("Picture Mode:"), 1, 0)
        self._picmode_combo = QComboBox()
        self._picmode_combo.setStyleSheet(_STYLE_COMBO)
        self._picmode_combo.addItems(["expert1", "expert2", "cinema", "isf_bright", "isf_dark"])
        options_layout.addWidget(self._picmode_combo, 1, 1)

        layout.addWidget(options_group)

        # DV Config group
        dv_group = QGroupBox("Dolby Vision Config")
        dv_group.setStyleSheet(file_group.styleSheet())
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

        # Upload button
        self._upload_btn = QPushButton("Upload LUT to TV")
        self._upload_btn.setStyleSheet(_STYLE_BTN_PRIMARY)
        self._upload_btn.setEnabled(False)
        self._upload_btn.clicked.connect(self._on_upload_clicked)
        layout.addWidget(self._upload_btn)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #4fc3f7; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(_STYLE_LABEL)
        return lbl

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
                self._status_label.setText(f"Unsupported file type: {p.suffix}")
                return
            self._lut_path = p
            self._file_label.setText(p.name)
            self._lut_info_label.setText(info)
            self._upload_btn.setEnabled(True)
        except Exception as e:
            self._status_label.setText(f"Parse error: {e}")

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
        target_text = self._target_combo.currentText()
        target = LUTTarget.BT709 if "709" in target_text else LUTTarget.BT2020
        pic_mode = self._picmode_combo.currentText()
        self._on_upload(self._loaded_lut, target, pic_mode)

    def _on_upload_dv(self):
        if not hasattr(self, "_dv_path"):
            return
        self._on_upload(self._dv_path, None, None)

    def set_status(self, text: str, error: bool = False):
        color = "#f44336" if error else "#4fc3f7"
        self._status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        self._status_label.setText(text)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_lut_panel.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/ui/lut_panel.py tests/unit/test_lut_panel.py
git commit -m "feat: LUTPanel UI with file browser, target selector, and upload button"
```

---

## Task 5: Hardware LUT Upload Tests

**Files:**
- Create: `tests/hardware/test_lut_hardware.py`

- [ ] **Step 1: Create hardware test skeleton**

```python
# tests/hardware/test_lut_hardware.py
import pytest
import numpy as np
from pathlib import Path
from app.tv.connection import ConnectionManager
from app.tv.upload import LUTUploader, LUTTarget
from app.tv.lut import LUT1D, LUT3D

TV_IP = "192.168.1.101"  # Update before running
FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def connected_mgr():
    mgr = ConnectionManager(TV_IP)
    await mgr.connect()
    yield mgr
    await mgr.disconnect()


@pytest.mark.hardware
async def test_upload_identity_1d_lut(connected_mgr):
    """Upload an identity 1D LUT — should be a no-op visually."""
    data = np.tile(np.linspace(0, 1, 1024, dtype=np.float32), (3, 1))
    lut = LUT1D(data=data)
    uploader = LUTUploader(client=connected_mgr.client, pic_mode="expert1")
    await uploader.upload_1d(lut)


@pytest.mark.hardware
async def test_upload_identity_3d_lut_bt709(connected_mgr):
    """Upload an identity 3D LUT to BT.709 slot — should be a no-op visually."""
    size = 17
    data = np.zeros((size, size, size, 3), dtype=np.float32)
    for r in range(size):
        for g in range(size):
            for b in range(size):
                data[r, g, b] = [r / (size - 1), g / (size - 1), b / (size - 1)]
    lut = LUT3D(data=data, size=size)
    uploader = LUTUploader(client=connected_mgr.client, pic_mode="expert1")
    await uploader.upload_3d(lut, target=LUTTarget.BT709)


@pytest.mark.hardware
async def test_upload_cube_file_from_disk(connected_mgr):
    """Parse a real .cube file and upload it."""
    from app.tv.lut import parse_cube
    cube_path = FIXTURES / "test_lut_17.cube"
    lut = parse_cube(cube_path)
    uploader = LUTUploader(client=connected_mgr.client, pic_mode="expert1")
    await uploader.upload_3d(lut, target=LUTTarget.BT709)
```

- [ ] **Step 2: Run all unit tests one final time**

```bash
pytest tests/unit/ -v
```

Expected: All previously passing tests still pass.

- [ ] **Step 3: Commit**

```bash
git add tests/hardware/test_lut_hardware.py
git commit -m "feat: hardware LUT upload integration tests (require real TV)"
```

---

## Task 6: Wire LUTPanel into MainWindow

**Files:**
- Modify: `app/ui/main_window.py`

- [ ] **Step 1: Add LUT panel to navigation**

In `app/ui/main_window.py`, after `_setup_discovery()` initialization, add:

```python
# In MainWindow.__init__, after self._setup_discovery():
self._lut_panel = LUTPanel(on_upload=self._handle_lut_upload)
```

Add to imports at top of `app/ui/main_window.py`:

```python
import asyncio
from app.ui.lut_panel import LUTPanel
from app.tv.upload import LUTUploader, LUTTarget
from app.tv.dv_config import load_dv_config
from app.tv.lut import LUT1D, LUT3D
from pathlib import Path
```

Add method to MainWindow:

```python
async def _handle_lut_upload(self, lut_or_path, target, pic_mode):
    """Dispatch upload based on type — called by LUTPanel."""
    if not self._managers:
        self._lut_panel.set_status("No TV connected", error=True)
        return
    # Upload to all connected TVs
    for ip, mgr in self._managers.items():
        if not mgr.is_connected:
            continue
        try:
            if isinstance(lut_or_path, Path):
                # Dolby Vision config
                from app.tv.dv_config import load_dv_config
                cfg = load_dv_config(lut_or_path)
                await cfg.upload(mgr.client)
                self._lut_panel.set_status(f"DV config uploaded to {ip}")
            else:
                uploader = LUTUploader(client=mgr.client, pic_mode=pic_mode or "expert1")
                if isinstance(lut_or_path, LUT1D):
                    await uploader.upload_1d(lut_or_path)
                    self._lut_panel.set_status(f"1D LUT uploaded to {ip}")
                elif isinstance(lut_or_path, LUT3D):
                    await uploader.upload_3d(lut_or_path, target=target)
                    self._lut_panel.set_status(f"3D LUT ({target.value}) uploaded to {ip}")
        except Exception as e:
            self._lut_panel.set_status(f"Upload failed: {e}", error=True)
```

Wire the "📁 LUT Files" nav button in `_build_ui` to show `self._lut_panel`:

```python
# In the nav_items loop in _build_ui, connect the LUT Files button:
# Replace the nav_items list with buttons that call self.set_content():
btn.clicked.connect(lambda checked, k=key: self._on_nav(k))
```

Add `_on_nav` method:

```python
def _on_nav(self, key: str):
    if key == "luts":
        self.set_content(self._lut_panel)
    # Other nav keys will route to their panels in subsequent sub-projects
```

- [ ] **Step 2: Run all unit tests**

```bash
pytest tests/unit/ -v
```

Expected: All tests pass.

- [ ] **Step 3: Launch the app and verify**

```bash
python -m app.main
```

Expected:
1. Window opens
2. Click "📁 LUT Files" in sidebar — LUT Files panel appears
3. Click "Browse…" — file picker opens, accepts .cube and .cal files
4. Select the identity .cube from `tests/fixtures/` — shows "3D LUT — 17³"
5. "Upload LUT to TV" button becomes enabled
6. Without a TV connected: clicking Upload shows "No TV connected" in red

- [ ] **Step 4: Final commit**

```bash
git add app/ui/main_window.py
git commit -m "feat: wire LUTPanel into MainWindow sidebar navigation"
```

---

## Running Tests

```bash
# Unit tests (no TV needed)
pytest tests/unit/ -v

# Hardware tests (update TV_IP in test_lut_hardware.py first)
pytest tests/hardware/test_lut_hardware.py -v -m hardware
```
