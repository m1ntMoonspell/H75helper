"""Android device mirroring window.

Launches the ``scrcpy`` binary as a subprocess.  On Windows the scrcpy
render surface is re-parented into a PySide6 QWidget via the Win32
``SetParent`` API so it appears as an integrated part of the application.
All input (touch, keyboard, scroll, rotation) is handled natively by scrcpy.

Dependencies
------------
* ``scrcpy`` binary on PATH – https://github.com/Genymobile/scrcpy/releases
* ``adb`` binary on PATH   – part of Android SDK Platform-Tools
* On Windows: ``pywin32`` (already used by the rest of H75 Helper) for
  window embedding.  If unavailable scrcpy opens in its own window.
"""

import os
import shutil
import subprocess
import sys

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QTimer


# ------------------------------------------------------------------ #
#  Public helper
# ------------------------------------------------------------------ #

def is_scrcpy_available() -> bool:
    """Return *True* if the ``scrcpy`` binary can be found on PATH."""
    return shutil.which("scrcpy") is not None


# ------------------------------------------------------------------ #
#  Mirror window
# ------------------------------------------------------------------ #

class AndroidMirrorWindow(QWidget):
    """Launches *scrcpy* for a given device serial.

    On **Windows** the SDL window created by scrcpy is stripped of its
    chrome and re-parented into this widget using Win32 API so that it
    looks like a native part of the application.  The user can resize
    this widget and the embedded scrcpy surface follows automatically.

    On **other platforms** (or when ``pywin32`` is missing) scrcpy runs
    in its own standalone window – still fully functional.
    """

    def __init__(self, serial: str):
        super().__init__(None)
        self.serial = serial
        self._process: subprocess.Popen | None = None
        self._embedded_hwnd: int = 0
        self._native_hwnd: int = 0
        self._stderr_path = ""

        self.setWindowTitle(f"Android Mirror - {serial}")
        self.setMinimumSize(200, 300)
        self.resize(360, 640)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_NativeWindow)

        self._build_ui()
        self.show()
        self._native_hwnd = int(self.winId())

        self._launch_scrcpy()

    # ---- UI ---------------------------------------------------------- #

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._status = QLabel("正在启动 scrcpy ...")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setWordWrap(True)
        self._status.setStyleSheet(
            "background:#000; color:#aaa; font-size:14px; padding:20px;"
        )
        self._status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self._status)

    # ---- scrcpy process ---------------------------------------------- #

    def _launch_scrcpy(self):
        scrcpy_exe = shutil.which("scrcpy")
        if not scrcpy_exe:
            self._status.setText(
                "未找到 scrcpy 命令。\n\n"
                "请从以下地址下载 scrcpy 并添加到系统 PATH:\n"
                "https://github.com/Genymobile/scrcpy/releases"
            )
            return

        scrcpy_dir = os.path.dirname(os.path.abspath(scrcpy_exe))
        self._scrcpy_title = f"H75Mirror_{self.serial}_{id(self)}"

        cmd = [
            scrcpy_exe,
            "-s", self.serial,
            "--window-title", self._scrcpy_title,
        ]

        import tempfile
        self._stderr_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", prefix="scrcpy_", delete=False,
        )
        self._stderr_path = self._stderr_file.name

        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=scrcpy_dir,
                stdout=subprocess.DEVNULL,
                stderr=self._stderr_file,
            )
        except OSError as exc:
            self._status.setText(f"启动 scrcpy 失败:\n{exc}")
            return

        # Periodic health-check
        self._health_timer = QTimer(self)
        self._health_timer.timeout.connect(self._check_process)
        self._health_timer.start(300)

        # On Windows, try to embed the scrcpy window inside this widget
        if sys.platform == "win32":
            self._embed_timer = QTimer(self)
            self._embed_timer.timeout.connect(self._try_embed)
            self._embed_timer.start(200)
            self._embed_attempts = 0

    # ---- Win32 window embedding -------------------------------------- #

    def _try_embed(self):
        """Periodically search for the scrcpy window and embed it."""
        try:
            import win32gui
            import win32con
        except ImportError:
            self._embed_timer.stop()
            return

        if self._process and self._process.poll() is not None:
            self._embed_timer.stop()
            return

        hwnd = win32gui.FindWindow(None, self._scrcpy_title)
        if not hwnd or not win32gui.IsWindow(hwnd):
            self._embed_attempts += 1
            if self._embed_attempts > 100:  # ~20 s
                self._embed_timer.stop()
            return

        if not self._native_hwnd or not win32gui.IsWindow(self._native_hwnd):
            self._native_hwnd = int(self.winId())
            if not win32gui.IsWindow(self._native_hwnd):
                return

        try:
            # Strip window chrome but keep it as a popup (NOT WS_CHILD,
            # because SDL crashes if its window becomes a child window)
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~(
                win32con.WS_CAPTION | win32con.WS_THICKFRAME
                | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX
                | win32con.WS_SYSMENU
            )
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex &= ~(
                win32con.WS_EX_DLGMODALFRAME | win32con.WS_EX_WINDOWEDGE
                | win32con.WS_EX_CLIENTEDGE | win32con.WS_EX_STATICEDGE
            )
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)

            win32gui.SetParent(hwnd, self._native_hwnd)

            self._embed_timer.stop()
            self._embedded_hwnd = hwnd
            self._status.hide()
            self._resize_embedded()
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        except Exception:
            self._embed_attempts += 1
            if self._embed_attempts > 100:
                self._embed_timer.stop()

    def _resize_embedded(self):
        if not self._embedded_hwnd:
            return
        try:
            import win32gui
            win32gui.MoveWindow(
                self._embedded_hwnd, 0, 0, self.width(), self.height(), True,
            )
        except Exception:
            pass

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._resize_embedded()

    # ---- process health ---------------------------------------------- #

    def _check_process(self):
        if not self._process:
            return
        ret = self._process.poll()
        if ret is None:
            return

        self._health_timer.stop()
        if hasattr(self, "_embed_timer"):
            self._embed_timer.stop()
        self._embedded_hwnd = 0
        self._status.show()

        stderr = self._read_stderr()

        if ret == 0:
            self._status.setText("连接已断开")
        else:
            msg = f"scrcpy 已退出 (code={ret})\n\n"
            if stderr:
                msg += stderr
            else:
                msg += (
                    "常见原因:\n"
                    "• 设备未开启 USB 调试\n"
                    "• 手机上未授权此电脑的 USB 调试\n"
                    "• scrcpy 缺少 DLL (请确保 scrcpy 目录下有\n"
                    "  SDL2.dll, avcodec 等文件)\n"
                    "• 数据线不支持数据传输 (仅充电线)"
                )
            self._status.setText(msg)

    def _read_stderr(self) -> str:
        try:
            if hasattr(self, "_stderr_file"):
                self._stderr_file.close()
            if self._stderr_path and os.path.isfile(self._stderr_path):
                with open(self._stderr_path, encoding="utf-8", errors="replace") as f:
                    return f.read(2000).strip()
        except Exception:
            pass
        return ""

    # ---- cleanup ----------------------------------------------------- #

    def closeEvent(self, ev):
        for name in ("_health_timer", "_embed_timer"):
            t = getattr(self, name, None)
            if t is not None:
                t.stop()
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
        try:
            if self._stderr_path and os.path.isfile(self._stderr_path):
                os.unlink(self._stderr_path)
        except Exception:
            pass
        super().closeEvent(ev)
