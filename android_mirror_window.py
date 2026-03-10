"""Android device mirroring window.

Launches the ``scrcpy`` binary as a subprocess.  On Windows the scrcpy
render surface is re-parented into a PySide6 QWidget via the Win32
``SetParent`` API so it appears as an integrated part of the application.
All input (touch, keyboard, scroll, rotation) is handled natively by scrcpy.
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
    """Return full path to ``scrcpy.exe`` or *None*."""
    found = shutil.which("scrcpy")
    if found:
        return os.path.abspath(found)

    base = Path(__file__).resolve().parent
    for name in ("scrcpy", "scrcpy-win64-v3.1", "scrcpy-win64-v3.0",
                 "scrcpy-win64-v2.7", "scrcpy-win64-v2.4"):
        candidate = base / name / ("scrcpy.exe" if sys.platform == "win32" else "scrcpy")
        if candidate.is_file():
            return str(candidate)
    return None


def is_scrcpy_available() -> bool:
    return _find_scrcpy() is not None


# ------------------------------------------------------------------ #
#  Mirror window
# ------------------------------------------------------------------ #

class AndroidMirrorWindow(QWidget):

    def __init__(self, serial: str):
        super().__init__(None)
        self.serial = serial
        self._process: subprocess.Popen | None = None
        self._embedded_hwnd: int = 0
        self._native_hwnd: int = 0

        self.setWindowTitle(f"Android Mirror - {serial}")
        self.setMinimumSize(200, 300)
        self.resize(360, 640)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_NativeWindow)

        self._build_ui()
        self.show()
        self._native_hwnd = int(self.winId())

        QTimer.singleShot(50, self._launch_scrcpy)

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

    # ---- scrcpy lifecycle -------------------------------------------- #

    def _launch_scrcpy(self):
        scrcpy_exe = _find_scrcpy()
        if not scrcpy_exe:
            self._status.setText(
                "未找到 scrcpy。\n\n"
                "请从以下地址下载并解压到本项目目录:\n"
                "https://github.com/Genymobile/scrcpy/releases"
            )
            return

        scrcpy_dir = os.path.dirname(scrcpy_exe)

        # ── diagnostic: can scrcpy start at all? ──
        try:
            kw: dict = {"capture_output": True, "text": True, "timeout": 5,
                        "cwd": scrcpy_dir}
            if sys.platform == "win32":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            ver = subprocess.run([scrcpy_exe, "--version"], **kw)
            if ver.returncode != 0:
                self._status.setText(
                    f"scrcpy 无法启动:\n{ver.stderr or ver.stdout}\n\n"
                    f"路径: {scrcpy_exe}\n"
                    "请检查目录中是否包含完整的 DLL 文件"
                )
                return
        except Exception as exc:
            self._status.setText(f"scrcpy 测试运行失败:\n{exc}\n\n路径: {scrcpy_exe}")
            return

        self._status.setText("scrcpy 验证通过，正在连接设备 ...")

        # ── actual launch ──
        self._scrcpy_title = f"H75Mirror_{self.serial}"

        cmd = [scrcpy_exe, "-s", self.serial,
               "--window-title", self._scrcpy_title]

        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=scrcpy_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            self._status.setText(f"启动 scrcpy 失败:\n{exc}")
            return

        self._health_timer = QTimer(self)
        self._health_timer.timeout.connect(self._check_process)
        self._health_timer.start(300)

        if sys.platform == "win32":
            self._embed_timer = QTimer(self)
            self._embed_timer.timeout.connect(self._try_embed)
            self._embed_timer.start(200)
            self._embed_attempts = 0

    # ---- Win32 window embedding -------------------------------------- #

    def _try_embed(self):
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
            if self._embed_attempts > 100:
                self._embed_timer.stop()
            return

        if not self._native_hwnd or not win32gui.IsWindow(self._native_hwnd):
            self._native_hwnd = int(self.winId())
            if not win32gui.IsWindow(self._native_hwnd):
                return

        try:
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

        stderr = ""
        try:
            raw = self._process.stderr.read()
            if raw:
                stderr = raw.decode(errors="replace").strip()
        except Exception:
            pass

        if ret == 0:
            self._status.setText("连接已断开")
        else:
            lines = [f"scrcpy 已退出 (code={ret})"]
            if stderr:
                lines.append("")
                lines.append(stderr[:1000])
            else:
                lines.append("")
                lines.append("可能的原因:")
                lines.append("  - 设备未开启 USB 调试")
                lines.append("  - 手机上未授权此电脑调试")
                lines.append("  - 数据线仅支持充电")
                lines.append("  - scrcpy 版本与设备不兼容")
                lines.append("")
                lines.append("请尝试在命令行中手动运行:")
                lines.append(f"  scrcpy -s {self.serial}")
            self._status.setText("\n".join(lines))

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
