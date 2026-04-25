# app/ui/main_window.py
import asyncio
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
from app.tv.upload import LUTUploader, LUTTarget
from app.tv.dv_config import load_dv_config
from app.tv.lut import LUT1D, LUT3D

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
        self._lut_panel = LUTPanel(on_upload=self._handle_lut_upload, parent=self)

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
            except Exception as e:
                logger.error("LUT upload failed for %s: %s", ip, e)
                self._lut_panel.set_status(f"Upload failed: {e}", error=True)

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
