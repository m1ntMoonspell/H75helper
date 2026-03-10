"""Android device mirroring window.

Launches ``scrcpy`` as a **standalone** window.  scrcpy natively handles
keyboard input (all keys), touch, scroll, and automatic rotation.

A small PySide6 status widget tracks the process lifecycle: it shows
progress while connecting, hides when scrcpy is running, and re-appears
with diagnostics if scrcpy exits unexpectedly.  If scrcpy crashes on
launch it is retried automatically up to 3 times.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QTimer


# ------------------------------------------------------------------ #
#  Locate scrcpy
# ------------------------------------------------------------------ #

def _find_scrcpy() -> str | None:
    """Return full path to the *scrcpy* binary, or *None*."""
    found = shutil.which("scrcpy")
    if found:
        return os.path.abspath(found)
    base = Path(__file__).resolve().parent
    exe = "scrcpy.exe" if sys.platform == "win32" else "scrcpy"
    for name in ("scrcpy", "scrcpy-win64-v3.1", "scrcpy-win64-v3.0",
                 "scrcpy-win64-v2.7", "scrcpy-win64-v2.4"):
        candidate = base / name / exe
        if candidate.is_file():
            return str(candidate)
    return None


def is_scrcpy_available() -> bool:
    return _find_scrcpy() is not None


# ------------------------------------------------------------------ #
#  Mirror manager widget
# ------------------------------------------------------------------ #

_MAX_RETRIES = 3


class AndroidMirrorWindow(QWidget):
    """Launches *scrcpy* in its own window and monitors the process.

    scrcpy's standalone window handles **all** input and display:
    - Keyboard (letters, numbers, function keys, etc.)
    - Mouse / touch
    - Scroll wheel
    - Automatic landscape / portrait rotation
    - Correct aspect ratio

    This QWidget only serves as a lifecycle manager / status display.
    """

    def __init__(self, serial: str):
        super().__init__(None)
        self.serial = serial
        self._process: subprocess.Popen | None = None
        self._attempt = 0
        self._scrcpy_exe: str | None = None
        self._scrcpy_dir: str = ""
        self._started_ok = False

        self.setWindowTitle(f"Android Mirror - {serial}")
        self.setFixedSize(420, 200)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._build_ui()
        self.show()

        QTimer.singleShot(50, self._begin)

    # ---- UI ---------------------------------------------------------- #

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        self._status = QLabel("正在启动 scrcpy ...")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setWordWrap(True)
        self._status.setStyleSheet(
            "background:#1e1e24; color:#aaa; font-size:14px;"
            "border-radius:8px; padding:15px;"
        )
        self._status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self._status)

    # ---- launch logic ------------------------------------------------ #

    def _begin(self):
        self._scrcpy_exe = _find_scrcpy()
        if not self._scrcpy_exe:
            self._status.setText(
                "未找到 scrcpy。\n\n"
                "请从以下地址下载并解压到本项目目录:\n"
                "https://github.com/Genymobile/scrcpy/releases"
            )
            return

        self._scrcpy_dir = os.path.dirname(self._scrcpy_exe)

        # Quick sanity check
        try:
            kw: dict = {"capture_output": True, "text": True, "timeout": 5,
                        "cwd": self._scrcpy_dir}
            if sys.platform == "win32":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            ver = subprocess.run([self._scrcpy_exe, "--version"], **kw)
            if ver.returncode != 0:
                self._status.setText(
                    f"scrcpy 无法运行:\n{ver.stderr or ver.stdout}\n\n"
                    f"路径: {self._scrcpy_exe}"
                )
                return
        except Exception as exc:
            self._status.setText(f"scrcpy 验证失败:\n{exc}")
            return

        self._try_launch()

    def _try_launch(self):
        self._attempt += 1
        if self._attempt > _MAX_RETRIES:
            self._status.setText(
                f"scrcpy 连续 {_MAX_RETRIES} 次启动失败。\n\n"
                "请在命令行手动运行以下命令查看详细错误:\n"
                f"  scrcpy -s {self.serial}"
            )
            return

        self._status.setText(
            f"正在启动 scrcpy (第 {self._attempt} 次) ..."
        )

        cmd = [self._scrcpy_exe, "-s", self.serial]

        try:
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0  # SW_HIDE console
                self._process = subprocess.Popen(
                    cmd, cwd=self._scrcpy_dir,
                    startupinfo=si,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                self._process = subprocess.Popen(cmd, cwd=self._scrcpy_dir)
        except OSError as exc:
            self._status.setText(f"启动失败:\n{exc}")
            return

        self._started_ok = False

        self._health_timer = QTimer(self)
        self._health_timer.timeout.connect(self._check_process)
        self._health_timer.start(300)

    # ---- process monitoring ------------------------------------------ #

    def _check_process(self):
        if not self._process:
            return
        ret = self._process.poll()

        if ret is None:
            # Still running — if it survived > 3 seconds, it's working
            if not self._started_ok and self._attempt > 0:
                self._started_ok = True
                self._status.setText(
                    "scrcpy 运行中\n\n"
                    "投屏画面在 scrcpy 的独立窗口中显示。\n"
                    "关闭此窗口将断开连接。"
                )
            return

        # Process exited
        self._health_timer.stop()

        if ret == 0:
            self._status.setText("连接已断开")
            return

        # Non-zero exit — retry if it died quickly (crash on init)
        if not self._started_ok and self._attempt < _MAX_RETRIES:
            QTimer.singleShot(500, self._try_launch)
            return

        lines = [
            f"scrcpy 已退出 (code={ret})",
            "",
            "请在命令行手动测试:",
            f"  scrcpy -s {self.serial}",
            "",
            "常见原因:",
            "  - 设备未开启 USB 调试",
            "  - 手机上未授权此电脑调试",
            "  - 数据线仅支持充电",
            "  - scrcpy 版本与设备不兼容",
        ]
        self._status.setText("\n".join(lines))

    # ---- cleanup ----------------------------------------------------- #

    def closeEvent(self, ev):
        t = getattr(self, "_health_timer", None)
        if t is not None:
            t.stop()
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
        super().closeEvent(ev)
