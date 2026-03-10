"""
Self-contained scrcpy client for Android screen mirroring.

Only requires ``av`` (PyAV) for H.264 decoding. All ADB operations use the
``adb`` command-line tool via subprocess so there is no dependency on
``adbutils`` or the ``scrcpy-client`` PyPI package.

Protocol compatible with scrcpy-server v1.25.
The server binary is auto-downloaded on first use from the official
Genymobile/scrcpy GitHub releases.
"""

import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import av

# ------------------------------------------------------------------ #
#  Protocol / version constants
# ------------------------------------------------------------------ #

SCRCPY_SERVER_VERSION = "1.25"
SCRCPY_SERVER_URL = (
    "https://github.com/Genymobile/scrcpy/releases/download/"
    f"v{SCRCPY_SERVER_VERSION}/scrcpy-server-v{SCRCPY_SERVER_VERSION}"
)
SERVER_REMOTE_PATH = "/data/local/tmp/scrcpy-server.jar"

# Touch / key action constants
ACTION_DOWN = 0
ACTION_UP = 1
ACTION_MOVE = 2

# Control message type codes
_TYPE_INJECT_KEYCODE = 0
_TYPE_INJECT_TEXT = 1
_TYPE_INJECT_TOUCH_EVENT = 2
_TYPE_INJECT_SCROLL_EVENT = 3
_TYPE_BACK_OR_SCREEN_ON = 4

# Android keycodes (commonly used subset)
KEYCODE_HOME = 3
KEYCODE_BACK = 4
KEYCODE_DPAD_UP = 19
KEYCODE_DPAD_DOWN = 20
KEYCODE_DPAD_LEFT = 21
KEYCODE_DPAD_RIGHT = 22
KEYCODE_VOLUME_UP = 24
KEYCODE_VOLUME_DOWN = 25
KEYCODE_POWER = 26
KEYCODE_TAB = 61
KEYCODE_SPACE = 62
KEYCODE_ENTER = 66
KEYCODE_DEL = 67
KEYCODE_MENU = 82
KEYCODE_SEARCH = 84
KEYCODE_FORWARD_DEL = 112


# ------------------------------------------------------------------ #
#  Helper: subprocess wrapper for ``adb``
# ------------------------------------------------------------------ #

def _adb(*args, serial=None, timeout=30):
    """Run an ``adb`` command and return *stdout* as a string."""
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    kw = {"capture_output": True, "text": True, "timeout": timeout}
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(cmd, **kw)


def _adb_bg(*args, serial=None):
    """Start an ``adb`` command in the background and return the *Popen*."""
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    kw = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(cmd, **kw)


# ------------------------------------------------------------------ #
#  scrcpy-server management
# ------------------------------------------------------------------ #

def _server_cache_path() -> Path:
    """Platform-appropriate cache directory for the server binary."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home())
    else:
        base = Path.home() / ".local" / "share"
    d = base / "H75Helper"
    d.mkdir(parents=True, exist_ok=True)
    return d / "scrcpy-server.jar"


def _ensure_server() -> str:
    """Return the local path to *scrcpy-server.jar*, downloading if absent."""
    path = _server_cache_path()
    if path.exists() and path.stat().st_size > 0:
        return str(path)

    print(f"[scrcpy] Downloading scrcpy-server v{SCRCPY_SERVER_VERSION} ...")
    req = urllib.request.Request(SCRCPY_SERVER_URL, headers={"User-Agent": "H75Helper/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    path.write_bytes(data)
    print(f"[scrcpy] Saved to {path} ({len(data):,} bytes)")
    return str(path)


# ------------------------------------------------------------------ #
#  Low-level helpers
# ------------------------------------------------------------------ #

def _recv_exactly(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("连接已关闭")
        buf.extend(chunk)
    return bytes(buf)


def _find_free_port(start: int = 27183, attempts: int = 100) -> int:
    for port in range(start, start + attempts):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", port))
            s.close()
            return port
        except OSError:
            continue
    raise RuntimeError("无法找到可用的本地端口")


# ------------------------------------------------------------------ #
#  ControlSender
# ------------------------------------------------------------------ #

class ControlSender:
    """Sends binary control messages over the scrcpy control socket."""

    def __init__(self, sock: socket.socket, resolution: tuple):
        self._sock = sock
        self.resolution = resolution  # (width, height)

    def touch(self, x, y, action=ACTION_DOWN, touch_id=0x1234567887654321):
        w, h = self.resolution
        pressure = 0xFFFF if action != ACTION_UP else 0
        self._sock.sendall(struct.pack(
            ">BBqiiHHHiI",
            _TYPE_INJECT_TOUCH_EVENT, action, touch_id,
            int(x), int(y), w, h, pressure, 1, 1,
        ))

    def keycode(self, keycode, action=ACTION_DOWN, repeat=0):
        self._sock.sendall(struct.pack(
            ">BBiiI",
            _TYPE_INJECT_KEYCODE, action, keycode, repeat, 0,
        ))

    def text(self, text):
        raw = text.encode("utf-8")
        self._sock.sendall(struct.pack(">BI", _TYPE_INJECT_TEXT, len(raw)) + raw)

    def scroll(self, x, y, h, v):
        sw, sh = self.resolution
        self._sock.sendall(struct.pack(
            ">BiiHHiiI",
            _TYPE_INJECT_SCROLL_EVENT, int(x), int(y), sw, sh, int(h), int(v), 0,
        ))

    def back_or_turn_screen_on(self, action=ACTION_DOWN):
        self._sock.sendall(struct.pack(">BB", _TYPE_BACK_OR_SCREEN_ON, action))


# ------------------------------------------------------------------ #
#  ScrcpyClient
# ------------------------------------------------------------------ #

class ScrcpyClient:
    """Self-contained scrcpy client.

    Usage::

        client = ScrcpyClient("SERIAL")
        client.on_frame = lambda data, w, h, stride: ...
        client.on_init  = lambda w, h: ...
        client.start()          # blocks – run in a thread
        # ... from another thread:
        client.control.touch(100, 200, ACTION_DOWN)
        client.stop()

    ``on_frame`` receives *(bytes, width, height, stride)* in **RGB24** format.
    ``stride`` is the bytes-per-row (may differ from ``width * 3`` due to
    alignment; pass it as the *bytesPerLine* argument to ``QImage``).
    """

    def __init__(
        self,
        serial: str,
        max_fps: int = 60,
        max_width: int = 0,
        bitrate: int = 8_000_000,
        stay_awake: bool = True,
        connection_timeout_ms: int = 10_000,
    ):
        self.serial = serial
        self.max_fps = max_fps
        self.max_width = max_width
        self.bitrate = bitrate
        self.stay_awake = stay_awake
        self.connection_timeout_ms = connection_timeout_ms

        # Callbacks – set by caller before start()
        self.on_frame = None        # (data: bytes, w: int, h: int, stride: int)
        self.on_init = None         # (w: int, h: int)
        self.on_disconnect = None   # ()

        self.control: ControlSender | None = None
        self.resolution = (0, 0)
        self.device_name = ""

        self._alive = False
        self._video_sock: socket.socket | None = None
        self._ctrl_sock: socket.socket | None = None
        self._server_proc: subprocess.Popen | None = None
        self._port = 0

    # ---- public ----

    def start(self):
        """Connect and stream.  **Blocks** until :meth:`stop` is called."""
        self._alive = True
        try:
            self._push_server()
            self._launch_server()
            self._connect()
            self._stream_loop()
        finally:
            self._cleanup()
            if self.on_disconnect:
                self.on_disconnect()

    def stop(self):
        self._alive = False
        for s in (self._video_sock, self._ctrl_sock):
            try:
                if s:
                    s.close()
            except Exception:
                pass

    # ---- internals ----

    def _push_server(self):
        local = _ensure_server()
        r = _adb("push", local, SERVER_REMOTE_PATH, serial=self.serial, timeout=30)
        if r.returncode != 0:
            raise RuntimeError(f"adb push 失败: {r.stderr.strip()}")

    def _launch_server(self):
        self._port = _find_free_port()

        # Set up ADB forward
        r = _adb("forward", f"tcp:{self._port}", "localabstract:scrcpy",
                 serial=self.serial)
        if r.returncode != 0:
            raise RuntimeError(f"adb forward 失败: {r.stderr.strip()}")

        # Build the shell command
        server_args = (
            f"CLASSPATH={SERVER_REMOTE_PATH} app_process / "
            f"com.genymobile.scrcpy.Server {SCRCPY_SERVER_VERSION} "
            f"log_level=info "
            f"max_size={self.max_width} "
            f"bit_rate={self.bitrate} "
            f"max_fps={self.max_fps} "
            f"lock_video_orientation=-1 "
            f"tunnel_forward=true "
            f"crop=- "
            f"send_frame_meta=true "
            f"control=true "
            f"display_id=0 "
            f"show_touches=false "
            f"stay_awake={'true' if self.stay_awake else 'false'} "
            f"codec_options=- "
            f"encoder_name=- "
            f"power_off_on_close=false "
            f"clipboard_autosync=true "
            f"downsize_on_error=true "
            f"cleanup=true "
            f"power_on=true"
        )
        self._server_proc = _adb_bg("shell", server_args, serial=self.serial)

    def _connect(self):
        deadline = time.monotonic() + self.connection_timeout_ms / 1000

        # Video socket (retry until server is ready)
        while time.monotonic() < deadline:
            try:
                self._video_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._video_sock.connect(("127.0.0.1", self._port))
                break
            except (ConnectionRefusedError, OSError):
                try:
                    self._video_sock.close()
                except Exception:
                    pass
                time.sleep(0.1)
        else:
            raise ConnectionError(
                f"无法连接到 scrcpy 服务端 (端口 {self._port})。\n"
                "请确保设备已启用 USB 调试且已授权此电脑。"
            )

        # Dummy byte
        _recv_exactly(self._video_sock, 1)

        # Control socket
        self._ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._ctrl_sock.connect(("127.0.0.1", self._port))

        # Device name (64 bytes, NUL-padded)
        self.device_name = (
            _recv_exactly(self._video_sock, 64)
            .decode("utf-8", errors="replace")
            .rstrip("\0")
        )

        # Initial resolution (2× unsigned short, big-endian)
        w, h = struct.unpack(">HH", _recv_exactly(self._video_sock, 4))
        self.resolution = (w, h)

        self.control = ControlSender(self._ctrl_sock, self.resolution)

        if self.on_init:
            self.on_init(w, h)

    def _stream_loop(self):
        codec = av.CodecContext.create("h264", "r")

        while self._alive:
            try:
                header = _recv_exactly(self._video_sock, 12)
                _pts, length = struct.unpack(">qI", header)
                raw_h264 = _recv_exactly(self._video_sock, length)

                for packet in codec.parse(raw_h264):
                    for frame in codec.decode(packet):
                        rgb = frame.reformat(format="rgb24")
                        w, h = rgb.width, rgb.height
                        plane = rgb.planes[0]
                        data = bytes(plane)
                        stride = plane.line_size

                        if (w, h) != self.resolution:
                            self.resolution = (w, h)
                            if self.control:
                                self.control.resolution = (w, h)

                        if self.on_frame:
                            self.on_frame(data, w, h, stride)
            except ConnectionError:
                break
            except Exception:
                if self._alive:
                    continue
                break

    def _cleanup(self):
        self._alive = False
        for s in (self._video_sock, self._ctrl_sock):
            try:
                if s:
                    s.close()
            except Exception:
                pass
        try:
            _adb("forward", "--remove", f"tcp:{self._port}", serial=self.serial)
        except Exception:
            pass
        if self._server_proc:
            try:
                self._server_proc.kill()
            except Exception:
                pass
