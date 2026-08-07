"""
System Skills - Windows app launching, command execution, window management
Using core.system modules
"""

from typing import List, Optional
from core.skills.base import BaseSkill, SkillParameter
from core.system import get_launcher, get_window_manager, get_shell_executor, get_screen_analyzer
import pyautogui
import time


class OpenAppSkill(BaseSkill):
    """Open/launch an application using AppLauncher."""
    
    @property
    def name(self) -> str:
        return "system.open_app"
    
    @property
    def description(self) -> str:
        return "Launch an installed application by name"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="app_name",
                type="string",
                description="Name of the application to open (e.g., 'chrome', 'vscode', 'whatsapp', 'notepad')",
                required=True,
            ),
            SkillParameter(
                name="arguments",
                type="string",
                description="Optional command line arguments",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Open Chrome",
            "Launch VS Code",
            "Start WhatsApp",
            "Open Notepad",
        ]
    
    def execute(self, app_name: str, arguments: str = "") -> str:
        """Launch the application using AppLauncher."""
        launcher = get_launcher()
        return launcher.launch(app_name, arguments)


class RunCommandSkill(BaseSkill):
    """Run a shell command using ShellExecutor."""
    
    @property
    def name(self) -> str:
        return "system.run_command"
    
    @property
    def description(self) -> str:
        return "Execute a shell command (PowerShell/CMD) - requires confirmation"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="command",
                type="string",
                description="Command to execute (PowerShell syntax)",
                required=True,
            ),
            SkillParameter(
                name="shell",
                type="string",
                description="Shell to use: 'powershell' or 'cmd'",
                required=False,
                default="powershell",
                enum=["powershell", "cmd"],
            ),
            SkillParameter(
                name="wait",
                type="boolean",
                description="Wait for command to complete",
                required=False,
                default=True,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def requires_confirmation(self) -> bool:
        return True
    
    @property
    def confirmation_message(self) -> str:
        return "This will execute a system command. Are you sure?"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Run command 'Get-Process'",
            "Execute 'ipconfig' in cmd",
            "Run PowerShell command 'ls'",
        ]
    
    def execute(self, command: str, shell: str = "powershell", wait: bool = True) -> str:
        """Execute the command using ShellExecutor."""
        executor = get_shell_executor()
        result = executor.execute(command, shell=shell, wait=wait)
        
        if result.success:
            output = result.stdout
            if result.stderr:
                output += f"\nWarnings: {result.stderr}"
            return output.strip() or "Command completed (no output)"
        else:
            return f"Command failed (exit {result.returncode}): {result.stderr}"


class VolumeControlSkill(BaseSkill):
    """Control system volume using pycaw."""
    
    @property
    def name(self) -> str:
        return "system.volume_control"
    
    @property
    def description(self) -> str:
        return "Get or set system volume"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="action",
                type="string",
                description="Action: 'get', 'set', 'mute', 'unmute', 'up', 'down'",
                required=True,
                enum=["get", "set", "mute", "unmute", "up", "down"],
            ),
            SkillParameter(
                name="level",
                type="number",
                description="Volume level 0-100 (for 'set' action)",
                required=False,
                default=50,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Set volume to 50",
            "Mute volume",
            "Increase volume",
            "What's the volume?",
        ]
    
    def execute(self, action: str, level: int = 50) -> str:
        """Control volume using Windows API (pycaw)."""
        try:
            from pycaw.pycaw import AudioUtilities
            
            devices = AudioUtilities.GetSpeakers()
            volume = devices.EndpointVolume
            
            if action == "get":
                current = volume.GetMasterVolumeLevelScalar()
                return f"Volume: {int(current * 100)}%"
            
            elif action == "set":
                level = max(0, min(100, level)) / 100.0
                volume.SetMasterVolumeLevelScalar(level, None)
                return f"Volume set to {int(level * 100)}%"
            
            elif action == "mute":
                volume.SetMute(1, None)
                return "Volume muted"
            
            elif action == "unmute":
                volume.SetMute(0, None)
                return "Volume unmuted"
            
            elif action == "up":
                current = volume.GetMasterVolumeLevelScalar()
                new_level = min(1.0, current + 0.1)
                volume.SetMasterVolumeLevelScalar(new_level, None)
                return f"Volume increased to {int(new_level * 100)}%"
            
            elif action == "down":
                current = volume.GetMasterVolumeLevelScalar()
                new_level = max(0.0, current - 0.1)
                volume.SetMasterVolumeLevelScalar(new_level, None)
                return f"Volume decreased to {int(new_level * 100)}%"
            
            return f"Unknown action: {action}"
            
        except ImportError:
            return "Volume control not available (install pycaw)"
        except Exception as e:
            return f"Volume control failed: {e}"


class ListWindowsSkill(BaseSkill):
    """List open windows using WindowManager."""
    
    @property
    def name(self) -> str:
        return "system.list_windows"
    
    @property
    def description(self) -> str:
        return "List all open windows"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="filter",
                type="string",
                description="Optional filter for window titles",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def examples(self) -> List[str]:
        return [
            "List open windows",
            "Show all windows",
            "Find Chrome windows",
        ]
    
    def execute(self, filter: str = "") -> str:
        """List open windows."""
        wm = get_window_manager()
        windows = wm.list_windows(filter)
        
        if not windows:
            return "No windows found" + (f" matching '{filter}'" if filter else "")
        
        lines = [f"Open windows ({len(windows)}):"]
        for w in windows[:20]:
            state = []
            if w.is_minimized:
                state.append("minimized")
            if w.is_maximized:
                state.append("maximized")
            state_str = f" [{', '.join(state)}]" if state else ""
            lines.append(f"  {w.title} (PID: {w.process_id}, {w.process_name}){state_str}")
        
        return "\n".join(lines)


class FocusWindowSkill(BaseSkill):
    """Focus/bring a window to front using WindowManager."""
    
    @property
    def name(self) -> str:
        return "system.focus_window"
    
    @property
    def description(self) -> str:
        return "Bring a window to the foreground by title"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="window_title",
                type="string",
                description="Partial or full window title to focus",
                required=True,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Focus Chrome",
            "Bring VS Code to front",
            "Switch to WhatsApp",
        ]
    
    def execute(self, window_title: str) -> str:
        """Focus window by title."""
        wm = get_window_manager()
        if wm.focus_window(window_title):
            return f"Focused window: {window_title}"
        else:
            return f"Window not found: {window_title}"


class MinimizeWindowSkill(BaseSkill):
    """Minimize a window."""
    
    @property
    def name(self) -> str:
        return "system.minimize_window"
    
    @property
    def description(self) -> str:
        return "Minimize a window by title"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="window_title",
                type="string",
                description="Window title to minimize",
                required=True,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    def execute(self, window_title: str) -> str:
        wm = get_window_manager()
        if wm.minimize_window(window_title):
            return f"Minimized: {window_title}"
        return f"Window not found: {window_title}"


class MaximizeWindowSkill(BaseSkill):
    """Maximize a window."""
    
    @property
    def name(self) -> str:
        return "system.maximize_window"
    
    @property
    def description(self) -> str:
        return "Maximize a window by title"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="window_title",
                type="string",
                description="Window title to maximize",
                required=True,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    def execute(self, window_title: str) -> str:
        wm = get_window_manager()
        if wm.maximize_window(window_title):
            return f"Maximized: {window_title}"
        return f"Window not found: {window_title}"


class ScreenshotSkill(BaseSkill):
    """Take a screenshot."""
    
    @property
    def name(self) -> str:
        return "system.screenshot"
    
    @property
    def description(self) -> str:
        return "Capture screenshot of screen or region"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="region",
                type="string",
                description="Region: 'full', 'monitor1', 'monitor2', or 'x,y,width,height'",
                required=False,
                default="full",
            ),
            SkillParameter(
                name="save_path",
                type="string",
                description="Optional path to save screenshot",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Take screenshot",
            "Screenshot monitor 1",
            "Capture region 100,100,800,600",
        ]
    
    def execute(self, region: str = "full", save_path: str = "") -> str:
        """Take screenshot."""
        analyzer = get_screen_analyzer()
        
        try:
            if region == "full":
                image = analyzer.capture_full_screen()
            elif region.startswith("monitor"):
                idx = int(region.replace("monitor", "")) if region != "monitor" else 1
                image = analyzer.capture_monitor(idx)
            else:
                # Parse x,y,width,height
                parts = [int(x.strip()) for x in region.split(",")]
                if len(parts) == 4:
                    from core.system.screen import ScreenRegion
                    sr = ScreenRegion(left=parts[0], top=parts[1], width=parts[2], height=parts[3])
                    image = analyzer.capture_region(sr)
                else:
                    return "Invalid region format. Use 'full', 'monitor1', or 'x,y,width,height'"
            
            path = analyzer.save_screenshot(image, save_path if save_path else None)
            return f"Screenshot saved to: {path}"
        except Exception as e:
            return f"Screenshot failed: {e}"


class ReadScreenSkill(BaseSkill):
    """Read/OCR screen content."""
    
    @property
    def name(self) -> str:
        return "system.read_screen"
    
    @property
    def description(self) -> str:
        return "OCR screen content or analyze with vision"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="mode",
                type="string",
                description="Mode: 'ocr' (extract text), 'describe' (analyze with vision), 'find' (find text)",
                required=False,
                default="ocr",
                enum=["ocr", "describe", "find"],
            ),
            SkillParameter(
                name="region",
                type="string",
                description="Region: 'full', 'monitor1', or 'x,y,width,height'",
                required=False,
                default="full",
            ),
            SkillParameter(
                name="query",
                type="string",
                description="Text to find (for 'find' mode) or custom prompt (for 'describe')",
                required=False,
                default="",
            ),
            SkillParameter(
                name="ocr_provider",
                type="string",
                description="OCR provider: 'tesseract', 'gemini_vision', 'nvidia_vision'",
                required=False,
                default="nvidia_vision",
                enum=["tesseract", "gemini_vision", "nvidia_vision"],
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Read screen text",
            "Describe what's on screen",
            "Find 'submit' button on screen",
        ]
    
    def execute(self, mode: str = "ocr", region: str = "full", query: str = "", ocr_provider: str = "nvidia_vision") -> str:
        """Read/analyze screen."""
        analyzer = get_screen_analyzer(ocr_provider)
        
        try:
            # Capture region
            if region == "full":
                image = analyzer.capture_full_screen()
            elif region.startswith("monitor"):
                idx = int(region.replace("monitor", "")) if region != "monitor" else 1
                image = analyzer.capture_monitor(idx)
            else:
                parts = [int(x.strip()) for x in region.split(",")]
                if len(parts) == 4:
                    from core.system.screen import ScreenRegion
                    sr = ScreenRegion(left=parts[0], top=parts[1], width=parts[2], height=parts[3])
                    image = analyzer.capture_region(sr)
                else:
                    return "Invalid region format"
            
            if mode == "ocr":
                text = analyzer.ocr(image)
                return f"Screen text:\n{text}" if text.strip() else "No text found on screen"
            
            elif mode == "describe":
                prompt = query or "Describe what's on this screen in detail"
                return analyzer.analyze_screen(prompt)
            
            elif mode == "find":
                if not query:
                    return "Query required for find mode"
                # OCR and search
                text = analyzer.ocr(image)
                if query.lower() in text.lower():
                    return f"Found '{query}' on screen"
                return f"'{query}' not found on screen"
            
            return f"Unknown mode: {mode}"
            
        except Exception as e:
            return f"Screen reading failed: {e}"


class TypeTextSkill(BaseSkill):
    """Type text into the currently focused window."""
    
    @property
    def name(self) -> str:
        return "system.type_text"
    
    @property
    def description(self) -> str:
        return "Type text into the currently active/focused window"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="text",
                type="string",
                description="Text to type",
                required=True,
            ),
            SkillParameter(
                name="interval",
                type="number",
                description="Interval between keystrokes in seconds",
                required=False,
                default=0.01,
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Type hello world in notepad",
            "Write a paragraph in notepad",
            "Type text in active window",
        ]
    
    def execute(self, text: str, interval: float = 0.01) -> str:
        """Type text into active window."""
        try:
            # Give user time to focus the target window
            time.sleep(0.5)
            pyautogui.write(text, interval=interval)
            return f"Typed text into active window"
        except Exception as e:
            return f"Failed to type text: {e}"


class SendScreenshotWhatsAppSkill(BaseSkill):
    """Take screenshot and send via WhatsApp Desktop."""
    
    @property
    def name(self) -> str:
        return "system.send_screenshot_whatsapp"
    
    @property
    def description(self) -> str:
        return "Take a screenshot and send it to a contact via WhatsApp Desktop"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="contact",
                type="string",
                description="Contact name to send screenshot to",
                required=True,
            ),
            SkillParameter(
                name="message",
                type="string",
                description="Optional message to send with screenshot",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "system"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Send screenshot to Ansh on WhatsApp",
            "Take screenshot and WhatsApp it to mom",
        ]
    
    def execute(self, contact: str, message: str = "") -> str:
        """Take screenshot and send via WhatsApp Desktop."""
        try:
            from pywinauto import Application
            import tempfile
            import os
            
            # Take screenshot
            analyzer = get_screen_analyzer()
            image = analyzer.capture_full_screen()
            screenshot_path = analyzer.save_screenshot(image)
            
            # Connect to WhatsApp Desktop
            app = Application(backend='uia').connect(class_name='WinUIDesktopWin32WindowClass')
            windows = app.windows()
            if not windows:
                return "WhatsApp window not found"
            window = windows[0]
            window.set_focus()
            time.sleep(0.5)
            
            # Find search box
            search_box = None
            for ctrl in window.descendants(control_type='Edit'):
                try:
                    if ctrl.automation_id() == '_r_a_':
                        search_box = ctrl
                        break
                except:
                    pass
            
            if not search_box:
                return "Could not find WhatsApp search box"
            
            # Search for contact
            search_box.click_input()
            time.sleep(0.3)
            search_box.type_keys('^a')
            time.sleep(0.2)
            search_box.type_keys(contact)
            time.sleep(2)
            
            # Find and click contact
            contact_found = False
            try:
                parent = search_box.parent()
                for ctrl in parent.children():
                    if ctrl.friendly_class_name() == 'GroupBox':
                        for btn in ctrl.descendants(control_type='Button'):
                            try:
                                text = btn.window_text()
                                if contact.lower() in text.lower() and 'last seen' in text.lower():
                                    btn.click_input()
                                    contact_found = True
                                    time.sleep(1)
                                    break
                            except:
                                pass
                        if contact_found:
                            break
            except:
                pass
            
            if not contact_found:
                for btn in window.descendants(control_type='Button'):
                    try:
                        text = btn.window_text()
                        if contact.lower() in text.lower() and 'last seen' in text.lower():
                            btn.click_input()
                            contact_found = True
                            time.sleep(1)
                            break
                    except:
                        pass
            
            if not contact_found:
                return f"Contact '{contact}' not found in WhatsApp"
            
            # Find attachment button (paperclip icon) and click it
            # Try to find the attach button
            attach_found = False
            for btn in window.descendants(control_type='Button'):
                try:
                    text = btn.window_text()
                    auto_id = btn.automation_id()
                    # Attach button usually has no text but has an icon
                    if 'attach' in text.lower() or 'attach' in auto_id.lower() or auto_id == 'attachButton':
                        btn.click_input()
                        attach_found = True
                        time.sleep(1)
                        break
                except:
                    pass
            
            if not attach_found:
                # Try clicking the paperclip area - usually near the message input
                # Use keyboard shortcut Ctrl+Shift+P for attach in some versions
                try:
                    window.type_keys('^+p')  # Ctrl+Shift+P
                    time.sleep(1)
                    attach_found = True
                except:
                    pass
            
            if not attach_found:
                return "Could not find attach button in WhatsApp"
            
            # In the file dialog, type the screenshot path
            # Wait for file dialog
            time.sleep(1)
            
            # Try to find the file dialog
            try:
                from pywinauto import Desktop
                file_dialog = Desktop(backend='uia').window(title_re='.*[Oo]pen.*|.*[Ff]ile.*')
                if file_dialog.exists(timeout=3):
                    # Find file path input
                    for ctrl in file_dialog.descendants(control_type='Edit'):
                        try:
                            ctrl.type_keys(screenshot_path)
                            time.sleep(0.5)
                            ctrl.type_keys('{ENTER}')
                            time.sleep(2)
                            break
                        except:
                            pass
            except:
                pass
            
            # Send message if provided
            if message:
                edits = list(window.descendants(control_type='Edit'))
                msg_box = None
                for ctrl in edits:
                    try:
                        if ctrl.automation_id() == '' and ctrl.window_text() == '':
                            msg_box = ctrl
                            break
                    except:
                        pass
                
                if msg_box:
                    msg_box.click_input()
                    time.sleep(0.3)
                    msg_box.type_keys(message)
                    time.sleep(0.5)
            
            # Press Enter to send
            window.type_keys('{ENTER}')
            
            return f"Screenshot sent to {contact} via WhatsApp Desktop"
            
        except Exception as e:
            return f"Failed to send screenshot via WhatsApp: {e}"


def register_system_skills(registry) -> None:
    """Register all system skills."""
    skills = [
        OpenAppSkill(),
        RunCommandSkill(),
        VolumeControlSkill(),
        ListWindowsSkill(),
        FocusWindowSkill(),
        MinimizeWindowSkill(),
        MaximizeWindowSkill(),
        ScreenshotSkill(),
        ReadScreenSkill(),
        TypeTextSkill(),
        SendScreenshotWhatsAppSkill(),
    ]
    
    for skill in skills:
        registry.register(skill.to_definition())