from mainWindow import MyWindow
from PySide6.QtWidgets import QApplication
from pathlib import Path
from settings import _resource_dir

import ctypes

if __name__ == "__main__":
    # Fix for Windows 10/11 Toast Notifications not showing up (goes straight to Action Center)
    myappid = 'm1nt.h75helper.app.1' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication()
    app.setQuitOnLastWindowClosed(False) # Prevents the app from dying when X is clicked
    
    style_path = _resource_dir() / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))
    window = MyWindow()
    window.show()
    app.exec()
