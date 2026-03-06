import win32gui
import win32con
import win32api
import win32process
import time

def find_windows_by_title(title):
    """Returns list of (hwnd, display_label) tuples for all visible windows matching the title."""
    windows = []
    def _enum_cb(hwnd, results):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) == title:
            results.append(hwnd)
    win32gui.EnumWindows(_enum_cb, windows)
    return windows

def get_window_choices(title):
    """
    Returns a list of (hwnd, label) tuples for populating a combo box.
    Each label includes the PID and class name to distinguish same-named windows.
    """
    if not title:
        return []
    hwnds = find_windows_by_title(title)
    choices = []
    for i, hwnd in enumerate(hwnds):
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        cls_name = win32gui.GetClassName(hwnd)
        label = f"{title}  [PID: {pid} | {cls_name}]"
        choices.append((hwnd, label))
    return choices

def send_command_to_hwnd(hwnd, command):
    """
    Sends the command to a specific HWND via background POST messages (WM_CHAR).
    Returns True on success, False on failure.
    """
    if not hwnd:
        return False
    try:
        for char in command:
            win32api.PostMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
            time.sleep(0.005)
            
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
        time.sleep(0.005)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
        return True
    except Exception as e:
        print(f"Background Auto-type error for hwnd {hwnd}: {e}")
        return False

def send_command_to_consoles(title, command):
    """
    Legacy: Finds the FIRST visible window with the exact title and sends command.
    """
    if not title:
        return False
        
    windows = find_windows_by_title(title)
    if not windows:
        return False
        
    return send_command_to_hwnd(windows[0], command)


def find_form_hwnd(widget):
    """Walk up the parent chain from widget to find the Form's selected console HWND.
    
    Returns the HWND int if found, 0 otherwise.
    """
    p = widget.parent() if widget else None
    while p:
        if hasattr(p, 'get_selected_hwnd'):
            return p.get_selected_hwnd()
        p = p.parent()
    return 0
