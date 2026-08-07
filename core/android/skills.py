"""
Android Skills - Intent handlers for Android device control
"""

from typing import List, Optional
from core.skills.base import BaseSkill, SkillParameter
from core.android.async_helper import run_async
from core.android.bridge import get_bridge_manager


class AndroidOpenAppSkill(BaseSkill):
    """Open app on Android device."""
    
    @property
    def name(self) -> str:
        return "android.open_app"
    
    @property
    def description(self) -> str:
        return "Open an app on connected Android device"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="package_name",
                type="string",
                description="Android package name (e.g., 'com.whatsapp', 'com.google.android.youtube')",
                required=True,
            ),
            SkillParameter(
                name="device_id",
                type="string",
                description="Target device ID (optional, uses first connected)",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def requires_confirmation(self) -> bool:
        return False
    
    @property
    def examples(self) -> List[str]:
        return [
            "Open WhatsApp on phone",
            "Launch YouTube on Android",
            "Open Chrome on my phone",
        ]
    
    def execute(self, package_name: str, device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.open_app(package_name))
            if result.get("success"):
                return f"Opened {package_name} on phone"
            return f"Failed: {result.get('error', 'Unknown error')}"
        except Exception as e:
            return f"Error: {e}"


class AndroidTapSkill(BaseSkill):
    """Tap on Android screen."""
    
    @property
    def name(self) -> str:
        return "android.tap"
    
    @property
    def description(self) -> str:
        return "Tap at coordinates on Android screen"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="x",
                type="number",
                description="X coordinate",
                required=True,
            ),
            SkillParameter(
                name="y",
                type="number",
                description="Y coordinate",
                required=True,
            ),
            SkillParameter(
                name="device_id",
                type="string",
                description="Target device ID",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def requires_confirmation(self) -> bool:
        return True
    
    @property
    def examples(self) -> List[str]:
        return [
            "Tap at 500 1000 on phone",
            "Click coordinates 100 200 on Android",
        ]
    
    def execute(self, x: int, y: int, device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.tap(x, y))
            if result.get("success"):
                return f"Tapped at ({x}, {y})"
            return f"Failed: {result.get('error')}"
        except Exception as e:
            return f"Error: {e}"


class AndroidSwipeSkill(BaseSkill):
    """Swipe on Android screen."""
    
    @property
    def name(self) -> str:
        return "android.swipe"
    
    @property
    def description(self) -> str:
        return "Swipe on Android screen"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="x1",
                type="number",
                description="Start X",
                required=True,
            ),
            SkillParameter(
                name="y1",
                type="number",
                description="Start Y",
                required=True,
            ),
            SkillParameter(
                name="x2",
                type="number",
                description="End X",
                required=True,
            ),
            SkillParameter(
                name="y2",
                type="number",
                description="End Y",
                required=True,
            ),
            SkillParameter(
                name="duration",
                type="number",
                description="Duration in ms",
                required=False,
                default=300,
            ),
            SkillParameter(
                name="device_id",
                type="string",
                description="Target device ID",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def requires_confirmation(self) -> bool:
        return True
    
    @property
    def examples(self) -> List[str]:
        return [
            "Swipe from 500 1500 to 500 500 on phone",
            "Scroll up on Android",
        ]
    
    def execute(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300, device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.swipe(x1, y1, x2, y2, duration))
            if result.get("success"):
                return f"Swiped from ({x1},{y1}) to ({x2},{y2})"
            return f"Failed: {result.get('error')}"
        except Exception as e:
            return f"Error: {e}"


class AndroidTypeTextSkill(BaseSkill):
    """Type text on Android."""
    
    @property
    def name(self) -> str:
        return "android.type_text"
    
    @property
    def description(self) -> str:
        return "Type text on Android device"
    
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
                name="device_id",
                type="string",
                description="Target device ID",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def requires_confirmation(self) -> bool:
        return True
    
    @property
    def examples(self) -> List[str]:
        return [
            "Type 'hello world' on phone",
            "Enter text on Android",
        ]
    
    def execute(self, text: str, device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.type_text(text))
            if result.get("success"):
                return f"Typed: {text}"
            return f"Failed: {result.get('error')}"
        except Exception as e:
            return f"Error: {e}"


class AndroidNotificationsSkill(BaseSkill):
    """Get Android notifications."""
    
    @property
    def name(self) -> str:
        return "android.get_notifications"
    
    @property
    def description(self) -> str:
        return "Get notifications from Android device"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="device_id",
                type="string",
                description="Target device ID",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Show phone notifications",
            "Read notifications from Android",
        ]
    
    def execute(self, device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.get_notifications())
            if result.get("success"):
                notifications = result.get("notifications", [])
                if not notifications:
                    return "No notifications"
                lines = ["Notifications:"]
                for n in notifications[:10]:
                    lines.append(f"  {n.get('package', 'Unknown')}: {n.get('title', '')} - {n.get('text', '')}")
                return "\n".join(lines)
            return f"Failed: {result.get('error')}"
        except Exception as e:
            return f"Error: {e}"


class AndroidMediaControlSkill(BaseSkill):
    """Control Android media."""
    
    @property
    def name(self) -> str:
        return "android.media_control"
    
    @property
    def description(self) -> str:
        return "Control media playback on Android (play/pause/next/previous)"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="action",
                type="string",
                description="Action: play, pause, next, previous, stop",
                required=True,
                enum=["play", "pause", "next", "previous", "stop"],
            ),
            SkillParameter(
                name="device_id",
                type="string",
                description="Target device ID",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Play music on phone",
            "Pause Android media",
            "Next track on phone",
        ]
    
    def execute(self, action: str, device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.media_control(action))
            if result.get("success"):
                return f"Media {action} sent"
            return f"Failed: {result.get('error')}"
        except Exception as e:
            return f"Error: {e}"


class AndroidAnswerCallSkill(BaseSkill):
    """Answer incoming call on Android."""
    
    @property
    def name(self) -> str:
        return "android.answer_call"
    
    @property
    def description(self) -> str:
        return "Answer incoming call on Android"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="device_id",
                type="string",
                description="Target device ID",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def requires_confirmation(self) -> bool:
        return True
    
    @property
    def examples(self) -> List[str]:
        return [
            "Answer call on phone",
            "Pick up Android call",
        ]
    
    def execute(self, device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.answer_call())
            if result.get("success"):
                return "Call answered"
            return f"Failed: {result.get('error')}"
        except Exception as e:
            return f"Error: {e}"


class AndroidDeclineCallSkill(BaseSkill):
    """Decline incoming call on Android."""
    
    @property
    def name(self) -> str:
        return "android.decline_call"
    
    @property
    def description(self) -> str:
        return "Decline incoming call on Android"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="device_id",
                type="string",
                description="Target device ID",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def requires_confirmation(self) -> bool:
        return True
    
    @property
    def examples(self) -> List[str]:
        return [
            "Decline call on phone",
            "Reject Android call",
        ]
    
    def execute(self, device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.decline_call())
            if result.get("success"):
                return "Call declined"
            return f"Failed: {result.get('error')}"
        except Exception as e:
            return f"Error: {e}"


class AndroidOpenYouTubeSkill(BaseSkill):
    """Open YouTube on Android."""
    
    @property
    def name(self) -> str:
        return "android.open_youtube"
    
    @property
    def description(self) -> str:
        return "Open YouTube app on Android and search/play"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="query",
                type="string",
                description="Search query (optional)",
                required=False,
                default="",
            ),
            SkillParameter(
                name="device_id",
                type="string",
                description="Target device ID",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Open YouTube on phone",
            "Play despacito on YouTube phone",
            "YouTube cat videos on Android",
        ]
    
    def execute(self, query: str = "", device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.open_youtube(query))
            if result.get("success"):
                return f"Opened YouTube on phone" + (f" with query: {query}" if query else "")
            return f"Failed: {result.get('error')}"
        except Exception as e:
            return f"Error: {e}"


class AndroidScreenshotSkill(BaseSkill):
    """Take screenshot on Android."""
    
    @property
    def name(self) -> str:
        return "android.screenshot"
    
    @property
    def description(self) -> str:
        return "Take screenshot on Android device"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="device_id",
                type="string",
                description="Target device ID",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Screenshot phone",
            "Capture Android screen",
        ]
    
    def execute(self, device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.take_screenshot())
            if result.get("success"):
                return f"Screenshot taken on phone"
            return f"Failed: {result.get('error')}"
        except Exception as e:
            return f"Error: {e}"


class AndroidDeviceInfoSkill(BaseSkill):
    """Get Android device info."""
    
    @property
    def name(self) -> str:
        return "android.device_info"
    
    @property
    def description(self) -> str:
        return "Get info about connected Android device"
    
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="device_id",
                type="string",
                description="Target device ID",
                required=False,
                default="",
            ),
        ]
    
    @property
    def category(self) -> str:
        return "android"
    
    @property
    def examples(self) -> List[str]:
        return [
            "Phone info",
            "Android device details",
        ]
    
    def execute(self, device_id: str = "") -> str:
        try:
            manager = get_bridge_manager()
            bridge = manager._bridges.get(device_id or "mock_001") or next(
                (b for b in manager._bridges.values() if b.is_connected), None)
        except Exception as e:
            return f"No Android device connected: {e}"
        
        if not bridge or not bridge.is_connected:
            return "No Android device connected"
        
        try:
            result = run_async(bridge.get_device_info())
            if result.get("success"):
                info = result.get("info", {})
                lines = ["Android Device Info:"]
                for k, v in info.items():
                    lines.append(f"  {k}: {v}")
                return "\n".join(lines)
            return f"Failed: {result.get('error')}"
        except Exception as e:
            return f"Error: {e}"


def _get_bridge(manager, device_id: str):
    """Legacy function - kept for compatibility."""
    if device_id:
        return manager.get_bridge(device_id)
    for dev in manager.list_devices():
        bridge = manager.get_bridge(dev.device_id)
        if bridge and bridge.is_connected:
            return bridge
    return None


def register_android_skills(registry) -> None:
    """Register all Android skills."""
    skills = [
        AndroidOpenAppSkill(),
        AndroidTapSkill(),
        AndroidSwipeSkill(),
        AndroidTypeTextSkill(),
        AndroidNotificationsSkill(),
        AndroidMediaControlSkill(),
        AndroidAnswerCallSkill(),
        AndroidDeclineCallSkill(),
        AndroidOpenYouTubeSkill(),
        AndroidScreenshotSkill(),
        AndroidDeviceInfoSkill(),
    ]
    
    for skill in skills:
        registry.register(skill.to_definition())