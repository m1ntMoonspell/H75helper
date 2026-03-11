import os
import shutil
import subprocess
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer


def _ensure_tool_paths():
    """Add project-local tool directories to PATH so that ``adb`` and
    ``scrcpy`` installed by ``setup.bat`` are found even when the system
    PATH has not been refreshed (requires reopening the terminal)."""
    base = Path(__file__).resolve().parent
    for d in [base / "platform-tools", base / "scrcpy"]:
        s = str(d)
        if d.is_dir() and s not in os.environ.get("PATH", ""):
            os.environ["PATH"] = s + os.pathsep + os.environ.get("PATH", "")

_ensure_tool_paths()


def _find_scrcpy() -> str | None:
    """Return full path to the scrcpy binary, or *None*."""
    found = shutil.which("scrcpy")
    if found:
        return os.path.abspath(found)
    base = Path(__file__).resolve().parent
    exe = "scrcpy.exe" if sys.platform == "win32" else "scrcpy"
    for name in ("scrcpy", "scrcpy-win64-v3.1", "scrcpy-win64-v3.0",
                 "scrcpy-win64-v2.7", "scrcpy-win64-v2.4"):
        c = base / name / exe
        if c.is_file():
            return str(c)
    return None


class DeviceScanner(QThread):
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


_MAX_RETRIES = 3


class AndroidTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scanner = None
        self._scrcpy_procs: dict[str, subprocess.Popen] = {}
        self._retry_count = 0
        self._current_serial = ""
        self.initUI()
        self.refresh_devices()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title = QLabel("Android Devices")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # --- device list + buttons ---
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

        btn_col = QVBoxLayout()
        btn_col.setSpacing(10)
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.setFixedWidth(100)
        self.refresh_btn = QPushButton("刷新设备")
        self.refresh_btn.setFixedWidth(100)
        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.setFixedWidth(100)
        self.disconnect_btn.setEnabled(False)
        btn_col.addWidget(self.connect_btn)
        btn_col.addWidget(self.refresh_btn)
        btn_col.addWidget(self.disconnect_btn)
        btn_col.addStretch()
        row.addLayout(btn_col)
        row.addStretch()

        layout.addLayout(row)

        # --- mirror status ---
        self.mirror_status = QLabel("")
        self.mirror_status.setWordWrap(True)
        self.mirror_status.setStyleSheet("color: #a0a0a0; font-size: 13px;")
        layout.addWidget(self.mirror_status)

        layout.addStretch()

        self.connect_btn.clicked.connect(self.connect_device)
        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.disconnect_btn.clicked.connect(self.disconnect_device)

        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._check_scrcpy)

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

    # ---- scrcpy connect / disconnect ----

    def connect_device(self):
        item = self.device_list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择一个设备")
            return
        serial = item.data(Qt.UserRole)

        if serial in self._scrcpy_procs:
            proc = self._scrcpy_procs[serial]
            if proc.poll() is None:
                self.mirror_status.setText(f"设备 {serial} 已在投屏中")
                return
            del self._scrcpy_procs[serial]

        scrcpy_exe = _find_scrcpy()
        if not scrcpy_exe:
            QMessageBox.critical(
                self, "未找到 scrcpy",
                "投屏功能需要 scrcpy 命令行工具。\n\n"
                "请从以下地址下载并解压到本项目目录:\n"
                "https://github.com/Genymobile/scrcpy/releases",
            )
            return

        self._current_serial = serial
        self._retry_count = 0
        self._scrcpy_exe = scrcpy_exe
        self._scrcpy_dir = os.path.dirname(scrcpy_exe)
        self._do_launch()

    def _do_launch(self):
        serial = self._current_serial
        self._retry_count += 1

        self.mirror_status.setText(
            f"正在启动 scrcpy 连接 {serial} ..."
            + (f" (第 {self._retry_count} 次)" if self._retry_count > 1 else "")
        )
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)

        cmd = f'"{self._scrcpy_exe}" -s {serial}'
        try:
            proc = subprocess.Popen(
                cmd, shell=True, cwd=self._scrcpy_dir,
            )
        except OSError as exc:
            self.mirror_status.setText(f"启动失败: {exc}")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            return

        self._scrcpy_procs[serial] = proc

        if not self._monitor_timer.isActive():
            self._monitor_timer.start(500)

    def disconnect_device(self):
        serial = self._current_serial
        if serial in self._scrcpy_procs:
            proc = self._scrcpy_procs.pop(serial)
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        self.mirror_status.setText("已断开连接")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self._retry_count = 0
        if not self._scrcpy_procs:
            self._monitor_timer.stop()

    def _check_scrcpy(self):
        for serial in list(self._scrcpy_procs):
            proc = self._scrcpy_procs[serial]
            ret = proc.poll()
            if ret is None:
                if self.mirror_status.text().startswith("正在启动"):
                    self.mirror_status.setText(
                        f"scrcpy 投屏中 [{serial}] — "
                        "投屏窗口由 scrcpy 独立显示"
                    )
                continue

            del self._scrcpy_procs[serial]

            if ret == 0:
                self.mirror_status.setText("投屏已结束")
                self.connect_btn.setEnabled(True)
                self.disconnect_btn.setEnabled(False)
            elif serial == self._current_serial and self._retry_count < _MAX_RETRIES:
                QTimer.singleShot(800, self._do_launch)
                return
            else:
                self.mirror_status.setText(
                    f"scrcpy 退出 (code={ret})\n"
                    f"请在命令行手动测试:  scrcpy -s {serial}"
                )
                self.connect_btn.setEnabled(True)
                self.disconnect_btn.setEnabled(False)

        if not self._scrcpy_procs:
            self._monitor_timer.stop()
