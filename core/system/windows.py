"""
WindowManager - Windows window management (focus, list, resize, etc.)
"""

import win32gui
import win32con
import win32process
import psutil
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class WindowInfo:
    """Information about a window."""
    hwnd: int
    title: str
    process_id: int
    process_name: str
    rect: Tuple[int, int, int, int]  # left, top, right, bottom
    is_visible: bool
    is_minimized: bool
    is_maximized: bool


class WindowManager:
    """Manage Windows windows."""
    
    def __init__(self):
        self._windows: List[WindowInfo] = []
    
    def refresh(self) -> List[WindowInfo]:
        """Refresh window list."""
        self._windows = []
        
        def enum_windows(hwnd: int, _: int) -> bool:
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # Only windows with titles
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        proc = psutil.Process(pid)
                        proc_name = proc.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pid = 0
                        proc_name = "unknown"
                    
                    rect = win32gui.GetWindowRect(hwnd)
                    placement = win32gui.GetWindowPlacement(hwnd)
                    is_minimized = placement[1] == win32con.SW_SHOWMINIMIZED
                    is_maximized = placement[1] == win32con.SW_SHOWMAXIMIZED
                    
                    self._windows.append(WindowInfo(
                        hwnd=hwnd,
                        title=title,
                        process_id=pid,
                        process_name=proc_name,
                        rect=rect,
                        is_visible=True,
                        is_minimized=is_minimized,
                        is_maximized=is_maximized,
                    ))
            return True
        
        win32gui.EnumWindows(enum_windows, 0)
        return self._windows
    
    def list_windows(self, filter_str: str = "") -> List[WindowInfo]:
        """List all windows, optionally filtered by title."""
        if not self._windows:
            self.refresh()
        
        if filter_str:
            filter_lower = filter_str.lower()
            return [w for w in self._windows if filter_lower in w.title.lower()]
        return self._windows
    
    def find_window(self, title: str) -> Optional[WindowInfo]:
        """Find window by partial title match."""
        windows = self.list_windows(title)
        return windows[0] if windows else None
    
    def focus_window(self, title: str) -> bool:
        """Bring window to foreground by title."""
        window = self.find_window(title)
        if not window:
            return False
        
        hwnd = window.hwnd
        
        # Restore if minimized
        if window.is_minimized:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # Bring to front
        try:
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            # Fallback: attach thread input
            try:
                import win32api
                current_thread = win32api.GetCurrentThreadId()
                target_thread = win32process.GetWindowThreadProcessId(hwnd)[0]
                win32process.AttachThreadInput(current_thread, target_thread, True)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32process.AttachThreadInput(current_thread, target_thread, False)
                return True
            except Exception:
                return False
    
    def minimize_window(self, title: str) -> bool:
        """Minimize window by title."""
        window = self.find_window(title)
        if not window:
            return False
        win32gui.ShowWindow(window.hwnd, win32con.SW_MINIMIZE)
        return True
    
    def maximize_window(self, title: str) -> bool:
        """Maximize window by title."""
        window = self.find_window(title)
        if not window:
            return False
        win32gui.ShowWindow(window.hwnd, win32con.SW_MAXIMIZE)
        return True
    
    def restore_window(self, title: str) -> bool:
        """Restore window (un-minimize/maximize) by title."""
        window = self.find_window(title)
        if not window:
            return False
        win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
        return True
    
    def close_window(self, title: str) -> bool:
        """Close window by title (sends WM_CLOSE)."""
        window = self.find_window(title)
        if not window:
            return False
        win32gui.PostMessage(window.hwnd, win32con.WM_CLOSE, 0, 0)
        return True
    
    def move_resize_window(self, title: str, x: int, y: int, width: int, height: int) -> bool:
        """Move and resize window by title."""
        window = self.find_window(title)
        if not window:
            return False
        win32gui.SetWindowPos(
            window.hwnd,
            win32con.HWND_TOP,
            x, y, width, height,
            win32con.SWP_SHOWWINDOW
        )
        return True
    
    def get_window_rect(self, title: str) -> Optional[Tuple[int, int, int, int]]:
        """Get window rectangle (left, top, right, bottom)."""
        window = self.find_window(title)
        if not window:
            return None
        return window.rect
    
    def set_always_on_top(self, title: str, on_top: bool = True) -> bool:
        """Set window always on top."""
        window = self.find_window(title)
        if not window:
            return False
        hwnd_insert = win32con.HWND_TOPMOST if on_top else win32con.HWND_NOTOPMOST
        win32gui.SetWindowPos(
            window.hwnd,
            hwnd_insert,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
        )
        return True


# Global instance
_window_manager = WindowManager()


def get_window_manager() -> WindowManager:
    return _window_manager