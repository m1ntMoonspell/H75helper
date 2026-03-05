from mainWindow import MyWindow
from PySide6.QtWidgets import QApplication
from pathlib import Path

import ctypes

if __name__ == "__main__":
    # Fix for Windows 10/11 Toast Notifications not showing up (goes straight to Action Center)
    myappid = 'm1nt.h75helper.app.1' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication()
    app.setQuitOnLastWindowClosed(False) # Prevents the app from dying when X is clicked
    
    style_path = Path(__file__).parent / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text())
    window = MyWindow()
    window.show()
    app.exec()
