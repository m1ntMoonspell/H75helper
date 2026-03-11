from mainWindow import MyWindow
from PySide6.QtWidgets import QApplication
from pathlib import Path
from settings import _resource_dir, CONFIG_PATH, save_config

import sys
import subprocess
import ctypes

def check_first_run():
    if not CONFIG_PATH.exists():
        save_config({})
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent
        setup_bat = base_dir / "setup.bat"
        if setup_bat.exists():
            subprocess.Popen([str(setup_bat)], cwd=str(base_dir), creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == "__main__":
    check_first_run()
    
    # Fix for Windows Toast Notifications
    if not getattr(sys, 'frozen', False):
        myappid = 'm1nt.h75helper.app.1' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication()
    app.setQuitOnLastWindowClosed(False) # Prevents the app from dying when X is clicked
    
    icon_path = _resource_dir() / "icon.png"
    if icon_path.exists():
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icon_path)))
        
    style_path = _resource_dir() / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))
    window = MyWindow()
    window.show()
    app.exec()
