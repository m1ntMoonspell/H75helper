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

import re
import subprocess
import sys

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QTimer


# ------------------------------------------------------------------ #
#  Public helper
# ------------------------------------------------------------------ #

def is_scrcpy_available() -> bool:
    """Return *True* if the ``scrcpy`` binary can be found on PATH."""
    try:
        kw: dict = {"capture_output": True, "timeout": 5}
        if sys.platform == "win32":
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        return subprocess.run(["scrcpy", "--version"], **kw).returncode == 0
    except FileNotFoundError:
        return False


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

        self.setWindowTitle(f"Android Mirror - {serial}")
        self.setMinimumSize(200, 300)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._init_geometry()
        self._build_ui()
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

    def _init_geometry(self):
        """Set initial size to match the device's aspect ratio."""
        try:
            kw: dict = {"capture_output": True, "text": True, "timeout": 5}
            if sys.platform == "win32":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            r = subprocess.run(
                ["adb", "-s", self.serial, "shell", "wm", "size"], **kw,
            )
            m = re.search(r"(\d+)x(\d+)", r.stdout)
            if m:
                w, h = int(m.group(1)), int(m.group(2))
                scale = 800 / max(w, h)
                self.resize(max(int(w * scale), 200), max(int(h * scale), 200))
                return
        except Exception:
            pass
        self.resize(360, 640)

    # ---- scrcpy process ---------------------------------------------- #

    def _launch_scrcpy(self):
        self._scrcpy_title = f"H75Mirror_{self.serial}_{id(self)}"

        cmd = [
            "scrcpy",
            "-s", self.serial,
            "--window-title", self._scrcpy_title,
        ]

        try:
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            self._status.setText(
                "未找到 scrcpy 命令。\n\n"
                "请从以下地址下载 scrcpy 并添加到系统 PATH:\n"
                "https://github.com/Genymobile/scrcpy/releases"
            )
            return

        # Periodic health-check
        self._health_timer = QTimer(self)
        self._health_timer.timeout.connect(self._check_process)
        self._health_timer.start(500)

        # On Windows, try to embed the scrcpy window inside this widget
        if sys.platform == "win32":
            self._embed_timer = QTimer(self)
            self._embed_timer.timeout.connect(self._try_embed)
            self._embed_timer.start(100)
            self._embed_attempts = 0

    # ---- Win32 window embedding -------------------------------------- #

    def _try_embed(self):
        """Periodically search for the scrcpy window and embed it."""
        try:
            import win32gui
            import win32con
        except ImportError:
            self._embed_timer.stop()
            if self._process and self._process.poll() is None:
                self._status.setText(
                    "scrcpy 已在独立窗口中启动\n"
                    "(安装 pywin32 可启用窗口内嵌)"
                )
            return

        hwnd = win32gui.FindWindow(None, self._scrcpy_title)
        if hwnd:
            self._embed_timer.stop()
            self._embedded_hwnd = hwnd

            # Strip window chrome ──────────────────────────────────
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~(
                win32con.WS_CAPTION | win32con.WS_THICKFRAME
                | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX
                | win32con.WS_SYSMENU
            )
            style |= win32con.WS_CHILD
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex &= ~(
                win32con.WS_EX_DLGMODALFRAME | win32con.WS_EX_WINDOWEDGE
                | win32con.WS_EX_CLIENTEDGE | win32con.WS_EX_STATICEDGE
            )
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)

            # Re-parent into our PySide6 widget ────────────────────
            win32gui.SetParent(hwnd, int(self.winId()))

            self._status.hide()
            self._resize_embedded()
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            return

        self._embed_attempts += 1
        if self._embed_attempts > 150:  # ~15 s
            self._embed_timer.stop()
            if self._process and self._process.poll() is None:
                self._status.setText("scrcpy 已在独立窗口中启动")

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

        stderr = ""
        try:
            stderr = self._process.stderr.read().decode(errors="replace").strip()
        except Exception:
            pass

        if ret == 0:
            self._status.setText("连接已断开")
        else:
            msg = f"scrcpy 已退出 (code={ret})"
            if stderr:
                msg += f"\n\n{stderr[:800]}"
            self._status.setText(msg)

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
        super().closeEvent(ev)
