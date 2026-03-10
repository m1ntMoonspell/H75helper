import subprocess
import sys
import re

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap

from scrcpy_client import (
    ScrcpyClient,
    ACTION_DOWN, ACTION_UP, ACTION_MOVE,
    KEYCODE_ENTER, KEYCODE_DEL, KEYCODE_FORWARD_DEL, KEYCODE_BACK,
    KEYCODE_HOME, KEYCODE_TAB, KEYCODE_SPACE,
    KEYCODE_DPAD_UP, KEYCODE_DPAD_DOWN, KEYCODE_DPAD_LEFT, KEYCODE_DPAD_RIGHT,
    KEYCODE_VOLUME_UP, KEYCODE_VOLUME_DOWN, KEYCODE_POWER, KEYCODE_MENU,
    KEYCODE_SEARCH,
)


class ScrcpyWorker(QThread):
    """Runs :class:`ScrcpyClient` in a background thread, forwarding frames."""

    frame_ready = Signal(object)            # (bytes, w, h, stride)
    resolution_changed = Signal(int, int)   # video width, height
    connection_error = Signal(str)

    def __init__(self, serial, max_fps=60, max_width=0, bitrate=8_000_000):
        super().__init__()
        self.serial = serial
        self.max_fps = max_fps
        self.max_width = max_width
        self.bitrate = bitrate
        self._client: ScrcpyClient | None = None
        self._prev_w = 0
        self._prev_h = 0

    @property
    def client(self) -> ScrcpyClient | None:
        return self._client

    def run(self):
        try:
            self._client = ScrcpyClient(
                self.serial,
                max_fps=self.max_fps,
                max_width=self.max_width,
                bitrate=self.bitrate,
            )
            self._client.on_frame = self._on_frame
            self._client.on_init = self._on_init
            self._client.start()  # blocks
        except Exception as exc:
            self.connection_error.emit(str(exc))

    def _on_init(self, w, h):
        self.resolution_changed.emit(w, h)

    def _on_frame(self, data, w, h, stride):
        if w != self._prev_w or h != self._prev_h:
            self._prev_w, self._prev_h = w, h
            self.resolution_changed.emit(w, h)
        self.frame_ready.emit((data, w, h, stride))

    def stop(self):
        if self._client:
            self._client.stop()


class AndroidMirrorWindow(QWidget):
    """Top-level window that mirrors an Android device screen via scrcpy.

    * Initialises to the device's native aspect ratio
    * Automatically adjusts when the device rotates (landscape / portrait)
    * Maps mouse press / move / release to touch events
    * Maps keyboard input to Android keycodes / text injection
    * Maps scroll wheel to scroll events
    """

    def __init__(self, serial):
        super().__init__(None)
        self.serial = serial
        self.frame_w = 0
        self.frame_h = 0
        self.setWindowTitle(f"Android Mirror - {serial}")
        self.setMinimumSize(200, 300)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._init_window_geometry()
        self._build_ui()
        self._start_worker()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.display = QLabel("正在连接...")
        self.display.setAlignment(Qt.AlignCenter)
        self.display.setStyleSheet(
            "background-color: #000; color: #aaa; font-size: 16px;"
        )
        self.display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.display)
        self.setMouseTracking(True)
        self.display.setMouseTracking(True)

    # ------------------------------------------------------------------ #
    #  Resolution / aspect-ratio helpers
    # ------------------------------------------------------------------ #

    def _init_window_geometry(self):
        """Query the physical screen size via ``adb shell wm size``."""
        try:
            kw = {"capture_output": True, "text": True, "timeout": 5}
            if sys.platform == "win32":
                kw["creationflags"] = subprocess.CREATE_NO_WINDOW
            r = subprocess.run(
                ["adb", "-s", self.serial, "shell", "wm", "size"], **kw
            )
            m = re.search(r"(\d+)x(\d+)", r.stdout)
            if m:
                self._apply_ratio(int(m.group(1)), int(m.group(2)))
                return
        except Exception:
            pass
        self.resize(360, 640)

    def _apply_ratio(self, w, h):
        cap = 800
        scale = cap / max(w, h)
        self.resize(max(int(w * scale), 200), max(int(h * scale), 200))

    # ------------------------------------------------------------------ #
    #  Scrcpy worker lifecycle
    # ------------------------------------------------------------------ #

    def _start_worker(self):
        self._worker = ScrcpyWorker(self.serial)
        self._worker.frame_ready.connect(self._on_frame, Qt.QueuedConnection)
        self._worker.resolution_changed.connect(self._on_res_changed)
        self._worker.connection_error.connect(self._on_error)
        self._worker.start()

    def _on_res_changed(self, w, h):
        self.frame_w, self.frame_h = w, h
        self._apply_ratio(w, h)

    def _on_frame(self, payload):
        data, w, h, stride = payload
        self.frame_w, self.frame_h = w, h
        img = QImage(data, w, h, stride, QImage.Format.Format_RGB888)
        pm = QPixmap.fromImage(img).scaled(
            self.display.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.display.setPixmap(pm)

    def _on_error(self, msg):
        self.display.setText(f"连接失败\n{msg}")

    # ------------------------------------------------------------------ #
    #  Coordinate mapping  (widget -> device)
    # ------------------------------------------------------------------ #

    def _to_device(self, pos):
        if not self.frame_w or not self.frame_h:
            return None, None
        lw, lh = self.display.width(), self.display.height()
        ar = self.frame_w / self.frame_h
        if ar > (lw / lh):
            rw, rh = lw, int(lw / ar)
        else:
            rw, rh = int(lh * ar), lh
        ox, oy = (lw - rw) // 2, (lh - rh) // 2
        x, y = pos.x() - ox, pos.y() - oy
        if x < 0 or y < 0 or x >= rw or y >= rh:
            return None, None
        return int(x / rw * self.frame_w), int(y / rh * self.frame_h)

    # ------------------------------------------------------------------ #
    #  Mouse -> touch
    # ------------------------------------------------------------------ #

    def _send_touch(self, ev, action):
        client = getattr(self, "_worker", None) and self._worker.client
        if not client or not client.control:
            return
        p = ev.position() if hasattr(ev, "position") else ev.localPos()
        dx, dy = self._to_device(p)
        if dx is None:
            return
        try:
            client.control.touch(dx, dy, action)
        except Exception:
            pass

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._send_touch(ev, ACTION_DOWN)

    def mouseMoveEvent(self, ev):
        if ev.buttons() & Qt.LeftButton:
            self._send_touch(ev, ACTION_MOVE)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._send_touch(ev, ACTION_UP)

    # ------------------------------------------------------------------ #
    #  Keyboard -> keycode / text
    # ------------------------------------------------------------------ #

    def keyPressEvent(self, ev):
        client = getattr(self, "_worker", None) and self._worker.client
        if not client or not client.control or ev.isAutoRepeat():
            return
        kc = _qt_to_android(ev.key())
        try:
            if kc is not None:
                client.control.keycode(kc, ACTION_DOWN)
            elif ev.text():
                client.control.text(ev.text())
        except Exception:
            pass

    def keyReleaseEvent(self, ev):
        client = getattr(self, "_worker", None) and self._worker.client
        if not client or not client.control or ev.isAutoRepeat():
            return
        kc = _qt_to_android(ev.key())
        if kc is not None:
            try:
                client.control.keycode(kc, ACTION_UP)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  Scroll -> scroll event
    # ------------------------------------------------------------------ #

    def wheelEvent(self, ev):
        client = getattr(self, "_worker", None) and self._worker.client
        if not client or not client.control:
            return
        p = ev.position() if hasattr(ev, "position") else ev.posF()
        dx, dy = self._to_device(p)
        if dx is None:
            return
        delta = ev.angleDelta()
        h = 1 if delta.x() > 0 else (-1 if delta.x() < 0 else 0)
        v = 1 if delta.y() > 0 else (-1 if delta.y() < 0 else 0)
        try:
            client.control.scroll(dx, dy, h, v)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  Cleanup
    # ------------------------------------------------------------------ #

    def closeEvent(self, ev):
        if hasattr(self, "_worker"):
            self._worker.stop()
            self._worker.wait(3000)
        super().closeEvent(ev)


# ------------------------------------------------------------------ #
#  Qt key -> Android keycode
# ------------------------------------------------------------------ #

_KEYMAP = {
    Qt.Key_Return:     KEYCODE_ENTER,
    Qt.Key_Enter:      KEYCODE_ENTER,
    Qt.Key_Backspace:  KEYCODE_DEL,
    Qt.Key_Delete:     KEYCODE_FORWARD_DEL,
    Qt.Key_Escape:     KEYCODE_BACK,
    Qt.Key_Home:       KEYCODE_HOME,
    Qt.Key_Tab:        KEYCODE_TAB,
    Qt.Key_Space:      KEYCODE_SPACE,
    Qt.Key_Up:         KEYCODE_DPAD_UP,
    Qt.Key_Down:       KEYCODE_DPAD_DOWN,
    Qt.Key_Left:       KEYCODE_DPAD_LEFT,
    Qt.Key_Right:      KEYCODE_DPAD_RIGHT,
    Qt.Key_VolumeUp:   KEYCODE_VOLUME_UP,
    Qt.Key_VolumeDown: KEYCODE_VOLUME_DOWN,
    Qt.Key_Menu:       KEYCODE_MENU,
    Qt.Key_Search:     KEYCODE_SEARCH,
    Qt.Key_PowerOff:   KEYCODE_POWER,
}


def _qt_to_android(qt_key):
    return _KEYMAP.get(qt_key)
