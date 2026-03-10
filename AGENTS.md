# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

H75 Helper is a **Windows-only** PySide6 desktop application for game QA testers. It has 5 tabs: GM Helper, Trace Helper, 日报 (Daily Report), 日历 (Holiday Calendar), and Android (device mirroring). Entry point is `main.py`.

### Windows-only limitation

The full application (`main.py` / `mainWindow.py`) **cannot run on Linux** because it depends on:
- `pywin32` (`win32gui`, `win32con`, `win32api`, `win32process`) — used in `auto_typer.py`
- `winreg` (stdlib, Windows-only) — used in `settings.py`
- `ctypes.windll` — used in `main.py`

### What CAN run on Linux

Individual modules without Windows dependencies can run standalone:
- `holiday_tab.py` — fully functional holiday countdown (fetches data from CDN)
- `android_tab.py` — Android device list UI (requires `adb` on PATH)
- `test_trans.py` — drag-and-drop test widget
- `custom_widgets.py`, `custom_toast.py` — pure PySide6 widgets

To run a PySide6 GUI on the Cloud VM, use DISPLAY=:1 (TigerVNC):
```
DISPLAY=:1 python3 holiday_tab.py
```

### Dependencies

No `requirements.txt` exists. Install manually:
```
pip install PySide6
```
For the Android mirroring tab (scrcpy protocol implemented in `scrcpy_client.py`):
```
pip install av
```
`pywin32` is not installable on Linux. ADB must be on PATH for Android device detection and mirroring.
The scrcpy-server binary is auto-downloaded on first connect (~40 KB from GitHub releases).

### Linting

No linter is configured in the repo. You can run:
```
ruff check .
```
There are ~14 pre-existing lint warnings (unused imports, ambiguous variable names) in the codebase.

### Tests

There is no automated test suite. `test_trans.py` is a manual GUI test widget, not an automated test.
