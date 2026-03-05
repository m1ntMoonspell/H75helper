from PySide6.QtWidgets import (QPushButton, QToolTip,
                               QDialog, QVBoxLayout, QLineEdit)
from PySide6.QtGui import QGuiApplication

class InputDia(QDialog):
    def __init__(self, text, title, parent=None):
        super().__init__(parent)
        self.creat_subwidgets(text, title)
        self.setWindowTitle("Input Dia")

    def creat_subwidgets(self, text, title):
        from PySide6.QtWidgets import QComboBox, QLineEdit
        from settings import load_config, save_config
        
        self.button = QPushButton("Confirm")
        self.button.setObjectName("primaryButton")
        
        if title == "重置宠物CD" or title == "觉醒单个宠物":
            self.edit = QComboBox(self)
            self.edit.setEditable(False)
            
            cfg = load_config()
            pet_options = cfg.get("pet_options", [
                "5 - 诺亚", "6 - 爱丽丝", "9 - 幻影", "11 - 游骑兵",
                "13 - 冰龙", "15 - 竹宝", "18 - 八筒", "20 - 金鳞"
            ])
            if "pet_options" not in cfg:
                cfg["pet_options"] = pet_options
                save_config(cfg)
                
            self.edit.addItems(pet_options)
        else:
            self.edit = QLineEdit(self)
            self.edit.setPlaceholderText("Enter text here...")
            
        self.button.clicked.connect(lambda checked,
                                    t=text: self.toclip(t, title=title))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        self.button.clicked.connect(self.reject)

    def toclip(self, text, title):
        from PySide6.QtWidgets import QComboBox
        
        if isinstance(self.edit, QComboBox):
            val = self.edit.currentText()
            if " - " in val:
                val = val.split(" - ")[0].strip()
        else:
            val = self.edit.text()
            
        if title == "重置宠物CD":
            command = f"{text}{val}"
        else:
            command = f"{text}({val})"
        
        from auto_typer import send_command_to_hwnd
        from custom_widgets import InAppToast
        
        # Walk up parent chain to find the Form with get_selected_hwnd
        hwnd = 0
        p = self.parent()
        while p:
            if hasattr(p, 'get_selected_hwnd'):
                hwnd = p.get_selected_hwnd()
                break
            p = p.parent()
        
        success = send_command_to_hwnd(hwnd, command) if hwnd else False
        
        if not success:
            cb = QGuiApplication.clipboard()
            cb.setText(command)
            
            # Walk up to the real main window (not this dialog)
            from PySide6.QtWidgets import QMainWindow
            main_win = None
            walker = self.parent()
            while walker:
                if isinstance(walker, QMainWindow):
                    main_win = walker
                    break
                walker = walker.parent()
            
            if main_win:
                toast = InAppToast("未找到目标控制台，已复制到剪贴板！", main_win, 2500)
                toast.setStyleSheet("""
                    QLabel {
                        background-color: #ED4245; 
                        color: #ffffff;
                        border-radius: 8px;
                        padding: 10px 20px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                toast.show_toast()
                main_win._fallback_toast = toast