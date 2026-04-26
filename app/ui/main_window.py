# app/ui/main_window.py
import asyncio
import datetime
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from app.tv.discovery import discover_tvs
from app.tv.connection import ConnectionManager
from app.tv.settings import LGTVSettings
from app.ui.discovery_panel import DiscoveryPanel
from app.ui.settings_panel import SettingsPanel
from app.ui.lut_panel import LUTPanel
from app.ui.measurement_panel import MeasurementPanel
from app.tv.upload import LUTUploader, LUTTarget
from app.tv.dv_config import load_dv_config
from app.tv.lut import LUT1D, LUT3D
from app.meter.argyll import ArgyllReader, list_argyll_devices, ArgyllNotFoundError
from app.generator.itpg import iTPGGenerator
from app.generator.pgenerator import PGeneratorClient
from app.measurement.patches import build_sdr_full, build_hdr10_full
from app.measurement.session import MeasurementSession
from app.measurement.store import save_cgats
from app.lut_gen.tone_curve import generate_1d_lut_from_grayscale
from app.lut_gen.gamut import generate_3d_lut_from_measurements

logger = logging.getLogger(__name__)


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
        self._managers: dict[str, ConnectionManager] = {}
        self._settings_panels: dict[str, SettingsPanel] = {}
        self._build_ui()
        self._setup_discovery()
        self._lut_panel = LUTPanel(
            on_upload=lambda *a: asyncio.ensure_future(self._handle_lut_upload(*a)),
            parent=self,
        )
        self._measurement_results = []
        self._measurement_panel = MeasurementPanel(
            on_run=self._on_measurement_action,
            on_upload_lut=lambda: asyncio.ensure_future(self._upload_measurement_luts()),
        )

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

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
            btn.clicked.connect(lambda checked, k=key: self._on_nav(k))
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: #111;")

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.content_stack, 1)

    def _setup_discovery(self):
        self._discovery_panel = DiscoveryPanel(on_connect=self._connect_to_tv)
        self._discovery_panel.tv_selected.connect(self._on_tv_selected)
        self.set_content(self._discovery_panel)

    def _on_nav(self, key: str):
        if key == "luts":
            self.set_content(self._lut_panel)
        elif key == "settings":
            for ip, panel in self._settings_panels.items():
                self.set_content(panel)
                return
            self.set_content(self._discovery_panel)
        elif key == "calibrate":
            self.set_content(self._measurement_panel)
        else:
            self.set_content(self._discovery_panel)

    def _on_tv_selected(self, ip: str, name: str):
        if ip == "__scan__":
            asyncio.ensure_future(self._run_scan())
        else:
            asyncio.ensure_future(self._connect_to_tv(ip, name))

    async def _run_scan(self):
        self._discovery_panel.set_scanning(True)
        try:
            tvs = await discover_tvs()
            self._discovery_panel.show_discovered(tvs)
        except Exception as e:
            logger.error("Scan failed: %s", e)
            self._discovery_panel.show_error(f"Scan failed: {e}")
        finally:
            self._discovery_panel.set_scanning(False)

    async def _connect_to_tv(self, ip: str, name: str):
        mgr = ConnectionManager(ip)
        try:
            await mgr.connect()
        except Exception as e:
            logger.error("Failed to connect to %s: %s", ip, e)
            self._discovery_panel.show_error(f"Connection failed: {e}")
            return
        self._managers[ip] = mgr
        self.update_tv_status(ip, name, connected=True)
        if mgr.firmware_warning:
            QMessageBox.warning(
                self,
                "Firmware Warning",
                f"webOS {mgr.snapshot.webos_version} detected.\n"
                "This firmware version may be incompatible with calibration commands.",
            )
        lgtv = LGTVSettings(client=mgr.client, pic_mode=mgr.snapshot.pic_mode)
        settings_panel = SettingsPanel(
            snapshot=mgr.snapshot,
            on_write=lambda coro: asyncio.ensure_future(coro),
        )
        settings_panel.set_connection(mgr, lgtv)
        self._settings_panels[ip] = settings_panel
        self.set_content(settings_panel)

    async def _handle_lut_upload(self, lut_or_path, target, pic_mode):
        """Dispatch LUT or DV config upload to all connected TVs."""
        if not self._managers:
            self._lut_panel.set_status("No TV connected", error=True)
            return
        for ip, mgr in self._managers.items():
            if not mgr.is_connected:
                continue
            try:
                if isinstance(lut_or_path, Path):
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
                    else:
                        logger.error("Unknown upload payload type: %s", type(lut_or_path))
            except Exception as e:
                logger.error("LUT upload failed for %s: %s", ip, e)
                self._lut_panel.set_status(f"Upload failed: {e}", error=True)

    def _on_measurement_action(self, action):
        if action == "__scan_meters__":
            asyncio.ensure_future(self._scan_meters())
        elif isinstance(action, dict) and action.get("action") == "measure":
            asyncio.ensure_future(self._run_measurement(action))

    async def _scan_meters(self):
        loop = asyncio.get_running_loop()
        try:
            devices = await loop.run_in_executor(None, list_argyll_devices)
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

        seq_name = config.get("sequence", "")
        if "HDR10" in seq_name:
            sequence = build_hdr10_full()
        else:
            sequence = build_sdr_full()

        if config.get("use_itpg"):
            generator = iTPGGenerator(client=mgr.client)
        else:
            pgen_ip = config.get("pgen_ip", "192.168.1.200")
            generator = PGeneratorClient(host=pgen_ip)

        meter_idx = config.get("meter_index", 0)
        reader = ArgyllReader(device_index=meter_idx)

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

    def update_tv_status(self, ip: str, name: str, connected: bool):
        if ip in self._tv_status_widgets:
            old = self._tv_status_widgets[ip]
            self._tv_status_area.removeWidget(old)
            old.deleteLater()
        widget = TVStatusWidget(name, connected, parent=self)
        self._tv_status_widgets[ip] = widget
        self._tv_status_area.addWidget(widget)

    def set_content(self, widget: QWidget):
        if self.content_stack.indexOf(widget) == -1:
            self.content_stack.addWidget(widget)
        self.content_stack.setCurrentWidget(widget)
