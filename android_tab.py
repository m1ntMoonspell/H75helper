import os
import subprocess
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal


def _ensure_tool_paths():
    """Add project-local tool directories to PATH so that ``adb`` and
    ``scrcpy`` installed by ``setup.bat`` are found even when the system
    PATH has not been refreshed (requires reopening the terminal)."""
    base = Path(__file__).resolve().parent
    extra = [
        base / "platform-tools",   # adb from setup.bat
        base / "scrcpy",           # scrcpy from setup.bat
    ]
    cur = os.environ.get("PATH", "")
    for d in extra:
        if d.is_dir() and str(d) not in cur:
            os.environ["PATH"] = str(d) + os.pathsep + cur
            cur = os.environ["PATH"]

_ensure_tool_paths()


class DeviceScanner(QThread):
    """Background thread – runs ``adb devices -l`` and parses the output."""

    devices_found = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            kw = {"capture_output": True, "text": True, "timeout": 10}
            if sys.platform == "win32":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(["adb", "devices", "-l"], **kw)
            devices = []
            for line in result.stdout.strip().splitlines()[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                serial, status = parts[0], parts[1]
                model = ""
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split(":", 1)[1]
                        break
                devices.append((serial, status, model))
            self.devices_found.emit(devices)
        except FileNotFoundError:
            self.error.emit(
                "未找到 adb 命令。\n"
                "请确保已安装 Android SDK Platform Tools 并添加到系统 PATH。"
            )
        except subprocess.TimeoutExpired:
            self.error.emit("ADB 命令超时，请检查 ADB 服务是否正常运行。")
        except Exception as e:
            self.error.emit(str(e))


class AndroidTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mirror_windows = {}
        self._scanner = None
        self.initUI()
        self.refresh_devices()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title = QLabel("Android Devices")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # --- square device-list panel + buttons beside it ---
        row = QHBoxLayout()
        row.setSpacing(15)

        self.device_frame = QFrame()
        self.device_frame.setObjectName("deviceFrame")
        self.device_frame.setFixedSize(340, 340)
        self.device_frame.setStyleSheet(
            "QFrame#deviceFrame {"
            "  background-color: #2b2b36;"
            "  border: 2px solid #3e3e4a;"
            "  border-radius: 8px;"
            "}"
        )
        frame_layout = QVBoxLayout(self.device_frame)

        self.device_list = QListWidget()
        self.device_list.setStyleSheet(
            "QListWidget { background: transparent; border: none;"
            "  color: #e0e0e0; font-size: 14px; }"
            "QListWidget::item { padding: 10px;"
            "  border-bottom: 1px solid #3e3e4a; }"
            "QListWidget::item:selected {"
            "  background: #5865F2; border-radius: 4px; }"
        )
        frame_layout.addWidget(self.device_list)

        self.status_label = QLabel("点击「刷新设备」扫描已连接的 Android 设备")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        frame_layout.addWidget(self.status_label)

        row.addWidget(self.device_frame)

        # Buttons beside the square frame
        btn_col = QVBoxLayout()
        btn_col.setSpacing(10)
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.setFixedWidth(100)
        self.refresh_btn = QPushButton("刷新设备")
        self.refresh_btn.setFixedWidth(100)
        btn_col.addWidget(self.connect_btn)
        btn_col.addWidget(self.refresh_btn)
        btn_col.addStretch()
        row.addLayout(btn_col)
        row.addStretch()

        layout.addLayout(row)
        layout.addStretch()

        self.connect_btn.clicked.connect(self.connect_device)
        self.refresh_btn.clicked.connect(self.refresh_devices)

    # ---- device scanning ----

    def refresh_devices(self):
        self.refresh_btn.setEnabled(False)
        self.status_label.setText("正在扫描设备...")
        self.device_list.clear()
        self._scanner = DeviceScanner()
        self._scanner.devices_found.connect(self._on_found)
        self._scanner.error.connect(self._on_error)
        self._scanner.finished.connect(lambda: self.refresh_btn.setEnabled(True))
        self._scanner.start()

    def _on_found(self, devices):
        self.device_list.clear()
        if not devices:
            self.status_label.setText("未发现已连接的 Android 设备")
            return
        self.status_label.setText(f"发现 {len(devices)} 个设备")
        for serial, status, model in devices:
            label = f"{model or serial}  [{serial}]  - {status}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, serial)
            if status != "device":
                item.setForeground(Qt.gray)
            self.device_list.addItem(item)
        self.device_list.setCurrentRow(0)

    def _on_error(self, msg):
        self.status_label.setText("扫描失败")
        QMessageBox.warning(self, "ADB 错误", msg)

    # ---- connect ----

    def connect_device(self):
        item = self.device_list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择一个设备")
            return
        serial = item.data(Qt.UserRole)

        if serial in self._mirror_windows:
            win = self._mirror_windows[serial]
            try:
                if win.isVisible():
                    win.activateWindow()
                    win.raise_()
                    return
            except RuntimeError:
                pass
            self._mirror_windows.pop(serial, None)

        from android_mirror_window import AndroidMirrorWindow, is_scrcpy_available

        if not is_scrcpy_available():
            QMessageBox.critical(
                self,
                "未找到 scrcpy",
                "投屏功能需要 scrcpy 命令行工具。\n\n"
                "请从以下地址下载并解压，然后将目录添加到系统 PATH:\n"
                "https://github.com/Genymobile/scrcpy/releases",
            )
            return

        try:
            win = AndroidMirrorWindow(serial)
            self._mirror_windows[serial] = win
            win.destroyed.connect(
                lambda _s=serial: self._mirror_windows.pop(_s, None)
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "连接失败", f"无法连接到设备 {serial}:\n{exc}"
            )
