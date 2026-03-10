import subprocess
import sys
import re

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap

import scrcpy
import adbutils


class ScrcpyWorker(QThread):
    """Runs the scrcpy client in a background thread, forwarding frames via signals."""

    frame_ready = Signal(object)            # numpy ndarray (BGR)
    resolution_changed = Signal(int, int)   # video width, height
    connection_error = Signal(str)

    def __init__(self, serial, max_fps=60, max_width=0, bitrate=8_000_000):
        super().__init__()
        self.serial = serial
        self.max_fps = max_fps
        self.max_width = max_width
        self.bitrate = bitrate
        self._client = None
        self._prev_w = 0
        self._prev_h = 0

    @property
    def client(self):
        return self._client

    def run(self):
        try:
            device = adbutils.AdbClient().device(self.serial)
            self._client = scrcpy.Client(
                device=device,
                max_fps=self.max_fps,
                max_width=self.max_width,
                bitrate=self.bitrate,
                stay_awake=True,
            )
            self._client.add_listener(scrcpy.EVENT_FRAME, self._on_frame)
            self._client.start(threaded=False)  # blocks in this QThread
        except Exception as exc:
            self.connection_error.emit(str(exc))

    def _on_frame(self, frame):
        if frame is None:
            return
        h, w = frame.shape[:2]
        if w != self._prev_w or h != self._prev_h:
            self._prev_w, self._prev_h = w, h
            self.resolution_changed.emit(w, h)
        self.frame_ready.emit(frame)

    def stop(self):
        if self._client:
            try:
                self._client.stop()
            except Exception:
                pass


class AndroidMirrorWindow(QWidget):
    """Top-level window that mirrors an Android device screen via scrcpy.

    Features:
    * Initialises to the device's native aspect ratio
    * Automatically adjusts when the device rotates (landscape / portrait)
    * Maps mouse press / move / release to touch events on the device
    * Maps keyboard input to Android keycodes / text injection
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

    def _on_frame(self, frame):
        h, w, _ = frame.shape
        self.frame_w, self.frame_h = w, h
        raw = frame.tobytes()
        img = QImage(raw, w, h, w * 3, QImage.Format.Format_BGR888)
        pm = QPixmap.fromImage(img).scaled(
            self.display.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.display.setPixmap(pm)

    def _on_error(self, msg):
        self.display.setText(f"连接失败\n{msg}")

    # ------------------------------------------------------------------ #
    #  Coordinate mapping  (widget → device)
    # ------------------------------------------------------------------ #

    def _to_device(self, pos):
        """Map a QPointF in widget-local coords to device pixel coords."""
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
    #  Mouse → touch
    # ------------------------------------------------------------------ #

    def _send_touch(self, ev, action):
        client = getattr(self, "_worker", None) and self._worker.client
        if not client:
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
            self._send_touch(ev, scrcpy.ACTION_DOWN)

    def mouseMoveEvent(self, ev):
        if ev.buttons() & Qt.LeftButton:
            self._send_touch(ev, scrcpy.ACTION_MOVE)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._send_touch(ev, scrcpy.ACTION_UP)

    # ------------------------------------------------------------------ #
    #  Keyboard → keycode / text
    # ------------------------------------------------------------------ #

    def keyPressEvent(self, ev):
        client = getattr(self, "_worker", None) and self._worker.client
        if not client or ev.isAutoRepeat():
            return
        kc = _qt_to_android(ev.key())
        try:
            if kc is not None:
                client.control.keycode(kc, scrcpy.ACTION_DOWN)
            elif ev.text():
                client.control.text(ev.text())
        except Exception:
            pass

    def keyReleaseEvent(self, ev):
        client = getattr(self, "_worker", None) and self._worker.client
        if not client or ev.isAutoRepeat():
            return
        kc = _qt_to_android(ev.key())
        if kc is not None:
            try:
                client.control.keycode(kc, scrcpy.ACTION_UP)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  Scroll → scroll event
    # ------------------------------------------------------------------ #

    def wheelEvent(self, ev):
        client = getattr(self, "_worker", None) and self._worker.client
        if not client:
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
#  Qt key → Android keycode mapping
# ------------------------------------------------------------------ #

_KEYMAP = {
    Qt.Key_Return:     scrcpy.KEYCODE_ENTER,
    Qt.Key_Enter:      scrcpy.KEYCODE_ENTER,
    Qt.Key_Backspace:  scrcpy.KEYCODE_DEL,
    Qt.Key_Delete:     scrcpy.KEYCODE_FORWARD_DEL,
    Qt.Key_Escape:     scrcpy.KEYCODE_BACK,
    Qt.Key_Home:       scrcpy.KEYCODE_HOME,
    Qt.Key_Tab:        scrcpy.KEYCODE_TAB,
    Qt.Key_Space:      scrcpy.KEYCODE_SPACE,
    Qt.Key_Up:         scrcpy.KEYCODE_DPAD_UP,
    Qt.Key_Down:       scrcpy.KEYCODE_DPAD_DOWN,
    Qt.Key_Left:       scrcpy.KEYCODE_DPAD_LEFT,
    Qt.Key_Right:      scrcpy.KEYCODE_DPAD_RIGHT,
    Qt.Key_VolumeUp:   scrcpy.KEYCODE_VOLUME_UP,
    Qt.Key_VolumeDown: scrcpy.KEYCODE_VOLUME_DOWN,
    Qt.Key_Menu:       scrcpy.KEYCODE_MENU,
    Qt.Key_Search:     scrcpy.KEYCODE_SEARCH,
    Qt.Key_PowerOff:   scrcpy.KEYCODE_POWER,
}


def _qt_to_android(qt_key):
    return _KEYMAP.get(qt_key)
