# app/ui/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt


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
        self._managers: dict = {}
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
            btn.clicked.connect(lambda checked, k=key: self._on_nav(k))
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Main content area
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: #111;")

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.content_stack, 1)

    def _on_nav(self, key: str):
        pass  # Filled in by Task 10 when panels are wired up

    def update_tv_status(self, ip: str, name: str, connected: bool):
        if ip in self._tv_status_widgets:
            old = self._tv_status_widgets[ip]
            self._tv_status_area.removeWidget(old)
            old.deleteLater()
        widget = TVStatusWidget(name, connected)
        self._tv_status_widgets[ip] = widget
        self._tv_status_area.addWidget(widget)

    def set_content(self, widget: QWidget):
        if self.content_stack.indexOf(widget) == -1:
            self.content_stack.addWidget(widget)
        self.content_stack.setCurrentWidget(widget)
