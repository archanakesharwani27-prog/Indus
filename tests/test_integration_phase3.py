"""
Phase 3 Integration Tests - System Control (Apps, Volume, Theme, Screenshots)
Tests system control with real Windows APIs.
Run: python -m pytest tests/test_integration_phase3.py -v -s
"""

import os
import sys
import pytest
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.system.launcher import AppLauncher
from core.system.windows import WindowManager, get_window_manager
from core.system.screen import ScreenAnalyzer, get_screen_analyzer
from pycaw.pycaw import AudioUtilities


@pytest.fixture(scope="module")
def app_launcher():
    return AppLauncher()


@pytest.fixture(scope="module")
def window_manager():
    return get_window_manager()


@pytest.fixture(scope="module")
def screen_analyzer():
    return get_screen_analyzer("nvidia_vision")


def test_list_running_apps(window_manager):
    """Test listing running applications."""
    apps = window_manager.list_windows()
    assert isinstance(apps, list)
    assert len(apps) > 0
    
    print(f"Found {len(apps)} windows")
    for app in apps[:5]:
        title = app.title.encode('ascii', 'replace').decode('ascii')
        print(f"  - {title} (pid: {app.process_id}, {app.process_name})")


def test_open_notepad(app_launcher):
    """Test opening Notepad."""
    result = app_launcher.launch("notepad")
    assert "Launched" in result or "Opened" in result, f"Failed to open Notepad: {result}"
    
    import time
    time.sleep(1)
    
    # Close it using window manager
    wm = get_window_manager()
    result = wm.close_window("Notepad")
    # Window title might be "Untitled - Notepad"
    if not result:
        result = wm.close_window("Untitled - Notepad")
    assert result is True, "Failed to close Notepad"


def test_open_calculator(app_launcher):
    """Test opening Calculator."""
    result = app_launcher.launch("calc")
    assert "Launched" in result or "Opened" in result, f"Failed to open Calculator: {result}"
    
    import time
    time.sleep(1)
    
    wm = get_window_manager()
    result = wm.close_window("Calculator")
    if not result:
        result = wm.close_window("कैलकुलेटर")  # Hindi name
    assert result is True, "Failed to close Calculator"


def test_volume_control():
    """Test volume get/set using pycaw."""
    devices = AudioUtilities.GetSpeakers()
    volume = devices.EndpointVolume
    
    # Get current volume
    current = volume.GetMasterVolumeLevelScalar()
    current_pct = int(current * 100)
    assert 0 <= current_pct <= 100, f"Invalid volume: {current_pct}"
    print(f"Current volume: {current_pct}%")
    
    # Set to 50%
    volume.SetMasterVolumeLevelScalar(0.5, None)
    
    import time
    time.sleep(0.5)
    
    new_vol = volume.GetMasterVolumeLevelScalar()
    new_pct = int(new_vol * 100)
    assert new_pct == 50, f"Volume not set correctly: {new_pct}"
    print(f"Volume set to: {new_pct}%")
    
    # Restore original
    volume.SetMasterVolumeLevelScalar(current, None)


def test_brightness_control():
    """Test brightness control via WMI (may not work on all systems)."""
    try:
        import wmi
        w = wmi.WMI(namespace='wmi')
        brightness_methods = w.WmiMonitorBrightnessMethods()
        
        if brightness_methods:
            # Get current brightness
            brightness_levels = w.WmiMonitorBrightness()
            current = brightness_levels[0].CurrentBrightness if brightness_levels else None
            print(f"Current brightness: {current}%")
            
            # Set to 50%
            for method in brightness_methods:
                method.WmiSetBrightness(50, 0)
            
            import time
            time.sleep(0.5)
            
            brightness_levels = w.WmiMonitorBrightness()
            new_bright = brightness_levels[0].CurrentBrightness if brightness_levels else None
            print(f"Brightness set to: {new_bright}%")
            
            # Restore
            if current is not None:
                for method in brightness_methods:
                    method.WmiSetBrightness(current, 0)
        else:
            print("Brightness control not supported on this system (no WmiMonitorBrightnessMethods)")
    except ImportError:
        print("Brightness control not available: wmi module not installed")
    except Exception as e:
        print(f"Brightness control not available: {e}")


def test_theme_toggle():
    """Test theme toggle via registry (requires explorer restart to take effect)."""
    import winreg
    
    # Read current theme
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            current = winreg.QueryValueEx(key, "AppsUseLightTheme")[0]
    except FileNotFoundError:
        current = 1  # Default light
    
    theme_name = "light" if current == 1 else "dark"
    print(f"Current theme: {theme_name}")
    
    # Toggle
    new_theme = 0 if current == 1 else 1
    new_theme_name = "dark" if new_theme == 0 else "light"
    
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 
                           0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, new_theme)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, new_theme)
        
        print(f"Theme registry set to: {new_theme_name} (requires explorer restart to apply)")
        
        # Restore
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 
                           0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, current)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, current)
    except PermissionError:
        print("Theme toggle requires admin or restart")


def test_screenshot_capture(screen_analyzer):
    """Test screenshot capture."""
    image = screen_analyzer.capture_full_screen()
    assert image is not None, "Failed to capture screenshot"
    
    path = screen_analyzer.save_screenshot(image)
    assert os.path.exists(path), f"Screenshot file not found: {path}"
    
    file_size = os.path.getsize(path)
    print(f"Screenshot saved: {path} ({file_size} bytes)")
    assert file_size > 1000, "Screenshot seems too small"
    
    # Cleanup
    os.unlink(path)


def test_region_screenshot(screen_analyzer):
    """Test region screenshot."""
    from core.system.screen import ScreenRegion
    
    # Capture a small region
    region = ScreenRegion(left=100, top=100, width=500, height=400)
    image = screen_analyzer.capture_region(region)
    assert image is not None, "Failed to capture region"
    
    path = screen_analyzer.save_screenshot(image)
    assert os.path.exists(path), f"Region screenshot not found: {path}"
    
    file_size = os.path.getsize(path)
    print(f"Region screenshot saved: {path} ({file_size} bytes)")
    
    # Cleanup
    os.unlink(path)


def test_mouse_position():
    """Test getting mouse position."""
    import win32api
    x, y = win32api.GetCursorPos()
    print(f"Mouse position: ({x}, {y})")
    assert isinstance(x, int) and isinstance(y, int)


def test_window_focus(window_manager):
    """Test focusing a window."""
    # Find a window to focus (e.g., any explorer window)
    windows = window_manager.list_windows("explorer")
    if windows:
        target = windows[0]
        result = window_manager.focus_window(target.title)
        print(f"Focused window: {target.title}")
        assert result is True, "Failed to focus window"
    else:
        print("No explorer window found to test focus")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])