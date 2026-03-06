from PySide6.QtWidgets import QPushButton, QDialog, QVBoxLayout, QLineEdit, QComboBox
from PySide6.QtGui import QGuiApplication

from auto_typer import send_command_to_hwnd, find_form_hwnd
from custom_widgets import show_error_toast
from settings import load_config, save_config


class InputDia(QDialog):
    def __init__(self, text, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Input Dia")
        self._build_ui(text, title)

    def _build_ui(self, text, title):
        self.button = QPushButton("Confirm")
        self.button.setObjectName("primaryButton")
        
        if title in ("重置宠物CD", "觉醒单个宠物"):
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
            
        self.button.clicked.connect(lambda checked, t=text: self._send(t, title))
        self.button.clicked.connect(self.reject)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)

    def _send(self, text, title):
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
        
        hwnd = find_form_hwnd(self)
        success = send_command_to_hwnd(hwnd, command) if hwnd else False
        
        if not success:
            show_error_toast(self, command)