import sys
import os
import winreg
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QCheckBox, QPushButton, QLabel, 
                               QHBoxLayout, QMessageBox, QTimeEdit, QFormLayout, QSlider, QLineEdit)
from PySide6.QtCore import QTime, Qt
from pathlib import Path

APP_NAME = "H75Helper"

def _resource_dir() -> Path:
    """
    PyInstaller onefile will extract resources to sys._MEIPASS.
    In source-run mode, fall back to this file's folder.
    """
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))

def _user_config_path() -> Path:
    """
    Persist user config in a stable per-user location when frozen.
    """
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        base = Path(appdata) if appdata else Path.home()
        cfg_dir = base / APP_NAME
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir / "config.json"
    return Path(__file__).parent / "config.json"

CONFIG_PATH = _user_config_path()
DEFAULT_CONFIG_PATH = _resource_dir() / "config.json"

def load_config():
    # Prefer persisted user config; otherwise fall back to packaged default.
    for p in (CONFIG_PATH, DEFAULT_CONFIG_PATH):
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return {}
    return {}

def save_config(data):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

class SettingsDia(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings / 设置")
        self.resize(350, 250)
        
        # Determine current exe or python script path
        if getattr(sys, 'frozen', False):
            self.app_path = sys.executable
        else:
            python_exe = sys.executable
            if python_exe.lower().endswith("python.exe"):
                python_exe = python_exe[:-10] + "pythonw.exe"
            self.app_path = f'"{python_exe}" "{Path(__file__).parent / "main.py"}"'
            
        self.reg_key = winreg.HKEY_CURRENT_USER
        self.reg_sub_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        self.app_name = "H75Helper"
        
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Settings")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        # Auto start toggle
        self.autostart_cb = QCheckBox("开机自启动 (Start on boot)")
        self.autostart_cb.setChecked(self.check_autostart_status())
        self.autostart_cb.stateChanged.connect(self.toggle_autostart)
        
        layout.addWidget(self.autostart_cb)
        
        # Load local config for timer settings
        self.config = load_config()
        self.m_hour, self.m_min = self.config.get("morning_time", [10, 30])
        self.n_hour, self.n_min = self.config.get("night_time", [18, 30])
        
        # Notification Times Layout
        form_layout = QFormLayout()
        self.morning_time_edit = QTimeEdit()
        self.morning_time_edit.setDisplayFormat("HH:mm")
        self.morning_time_edit.setButtonSymbols(QTimeEdit.NoButtons)
        self.morning_time_edit.setTime(QTime(self.m_hour, self.m_min))
        self.morning_time_edit.timeChanged.connect(self.save_times)
        
        self.night_time_edit = QTimeEdit()
        self.night_time_edit.setDisplayFormat("HH:mm")
        self.night_time_edit.setButtonSymbols(QTimeEdit.NoButtons)
        self.night_time_edit.setTime(QTime(self.n_hour, self.n_min))
        self.night_time_edit.timeChanged.connect(self.save_times)
        
        form_layout.addRow("上班提醒时间:", self.morning_time_edit)
        form_layout.addRow("下班提醒时间:", self.night_time_edit)
        
        # Floating window settings
        self.floating_cb = QCheckBox("启用日历悬浮窗 (Floating Holiday)")
        self.floating_cb.setChecked(self.config.get("holiday_floating_enabled", False))
        self.floating_cb.stateChanged.connect(self.save_floating_cfg)
        
        opacity_val = self.config.get("holiday_floating_opacity", 80)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(opacity_val)
        self.opacity_slider.valueChanged.connect(self.save_floating_cfg)
        
        op_layout = QHBoxLayout()
        self.op_label = QLabel(f"悬浮窗不透明度: {opacity_val}%")
        op_layout.addWidget(self.op_label)
        op_layout.addWidget(self.opacity_slider)
        
        layout.addLayout(form_layout)
        
        # Console window title setting
        self.console_title_edit = QLineEdit()
        self.console_title_edit.setText(self.config.get("console_title", "Console"))
        self.console_title_edit.textChanged.connect(self.save_console_cfg)
        layout.addWidget(QLabel("目标控制台窗口标题 (Console Window Title):"))
        layout.addWidget(self.console_title_edit)
        
        layout.addWidget(self.floating_cb)
        layout.addLayout(op_layout)
        
        # Open Config Button
        open_cfg_btn = QPushButton("打开 Config.json")
        open_cfg_btn.clicked.connect(self.open_config_file)
        layout.addWidget(open_cfg_btn)
        
        layout.addStretch()
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
    def save_floating_cfg(self):
        self.config["holiday_floating_enabled"] = self.floating_cb.isChecked()
        val = self.opacity_slider.value()
        self.config["holiday_floating_opacity"] = val
        self.op_label.setText(f"悬浮窗不透明度: {val}%")
        save_config(self.config)
        
    def save_console_cfg(self):
        self.config["console_title"] = self.console_title_edit.text()
        save_config(self.config)
        
    def save_times(self):
        m_time = self.morning_time_edit.time()
        n_time = self.night_time_edit.time()
        
        self.config["morning_time"] = [m_time.hour(), m_time.minute()]
        self.config["night_time"] = [n_time.hour(), n_time.minute()]
        save_config(self.config)
        
    def open_config_file(self):
        try:
            if not CONFIG_PATH.exists():
                save_config(self.config)
            os.startfile(str(CONFIG_PATH))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"无法打开文件:\n{e}")
        
    def check_autostart_status(self):
        try:
            key = winreg.OpenKey(self.reg_key, self.reg_sub_key, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, self.app_name)
            winreg.CloseKey(key)
            return value == self.app_path
        except FileNotFoundError:
            return False
            
    def toggle_autostart(self, state):
        try:
            key = winreg.OpenKey(self.reg_key, self.reg_sub_key, 0, winreg.KEY_ALL_ACCESS)
            if state:
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, self.app_path)
            else:
                try:
                    winreg.DeleteValue(key, self.app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"修改注册表失败:\n{e}")
            self.autostart_cb.setChecked(not state)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    dia = SettingsDia()
    dia.show()
    app.exec()
