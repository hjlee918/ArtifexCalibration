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
