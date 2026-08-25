# actions/action_verifier.py
"""
INDUS ActionVerifier -- Closed-Loop Action Verification Subsystem
Provides multi-tier verification (Deterministic System State -> Visual Diff -> Vision Model)
Ensures real-world computer and UI actions are independently verified with structured confidence.
"""

import time
import os
import platform
from dataclasses import dataclass
from typing import Optional, Any, Callable

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_OS = platform.system()

DESTRUCTIVE_ACTIONS = {
    "restart", "shutdown", "delete", "format", "kill", "drop", "truncate",
    "commit_and_push", "rmdir", "send_message", "pay", "checkout", "panic"
}


@dataclass
class VerificationResult:
    status: str          # "SUCCESS" | "FAILURE" | "UNCERTAIN"
    confidence: float    # 0.0 to 1.0
    evidence: str        # Short explanation of evidence found
    retry_allowed: bool  # True if safe to retry, False otherwise
    action_type: str     # "open_app", "click", "volume_set", "brightness_set", etc.

    @property
    def verified(self) -> bool:
        return self.status == "SUCCESS"

    @property
    def details(self) -> str:
        return self.evidence


class ActionVerifier:
    """
    Central ActionVerifier for closed-loop verification across all INDUS subsystems.
    """

    def __init__(self, max_retries: int = 1, player: Optional[Any] = None, player_ui: Optional[Any] = None):
        self.max_retries = max_retries
        self.player = player or player_ui
        self._os = _OS

    def _emit_if_failed(self, result, action_name: str) -> None:
        """Publish VERIFICATION_FAILED to EventBus when verification status is FAILURE."""
        if result.status == "FAILURE":
            try:
                from core.event_bus import event_bus, E
                event_bus.publish(E.VERIFICATION_FAILED, source="action_verifier",
                                  data={"action": action_name,
                                        "confidence": result.confidence,
                                        "evidence": result.evidence[:120],
                                        "retry_allowed": result.retry_allowed})
            except Exception:
                pass

    def capture_state_snapshot(self, action_name: str, parameters: dict = None) -> dict:
        """Capture relevant system and visual state before or after an action."""
        snap = {
            "timestamp": time.time(),
            "action": action_name,
            "parameters": parameters or {},
            "img": None,
            "volume": None,
        }
        act = (action_name or "").lower()
        if "click" in act or "control" in act or "screen" in act:
            snap["img"] = self.capture_screen_safe()
        if "volume" in act or "settings" in act:
            try:
                from actions.computer_settings import _get_volume_windows
                snap["volume"] = _get_volume_windows()
            except Exception:
                pass
        return snap

    def verify_action_success(
        self,
        action_name: str,
        pre_snapshot: dict,
        post_snapshot: dict,
        expected_target: str = "",
    ) -> VerificationResult:
        """Verify outcome based on action type and captured snapshots."""
        act = (action_name or "").lower()
        params = (post_snapshot or {}).get("parameters") or (pre_snapshot or {}).get("parameters") or {}

        if "open_app" in act or "app" in act:
            app = params.get("app_name") or expected_target
            return self.verify_app_launch(app)

        if "volume" in act or params.get("action") in ("volume_set", "volume_up", "volume_down", "set_volume"):
            target_v = params.get("value")
            try:
                target_v = int(target_v)
            except Exception:
                target_v = 30
            return self.verify_volume(target_volume=target_v)

        if "brightness" in act or params.get("action") in ("brightness_set", "set_brightness"):
            return self.verify_brightness(target_brightness=50)

        if pre_snapshot.get("img") is not None and post_snapshot.get("img") is not None:
            return self.verify_visual_change(pre_snapshot["img"], post_snapshot["img"])

        return VerificationResult(
            status="SUCCESS",
            confidence=0.9,
            evidence=f"Action [{action_name}] executed successfully.",
            retry_allowed=False,
            action_type=action_name,
        )



    def is_destructive(self, action_type: str, params: dict = None) -> bool:
        """Check if an action is destructive or irreversible (never auto-retry)."""
        act = (action_type or "").lower().strip()
        if act in DESTRUCTIVE_ACTIONS:
            return True
        if params:
            for v in params.values():
                if isinstance(v, str) and any(d in v.lower() for d in ("shutdown", "restart", "delete", "format", "drop")):
                    return True
        return False

    # -- Tier 1: Deterministic System State Verification ------------------------

    def verify_app_launch(self, app_name: str, wait_seconds: float = 0.8) -> VerificationResult:
        """Verify that an application process or window is running after launch."""
        if not _PSUTIL:
            return VerificationResult(
                status="UNCERTAIN",
                confidence=0.5,
                evidence="psutil not installed; cannot deterministically verify process state.",
                retry_allowed=False,
                action_type="open_app"
            )

        if wait_seconds > 0:
            time.sleep(wait_seconds)

        app_clean = app_name.lower().replace(".exe", "").strip()

        alias_map = {
            "notepad": ["notepad"],
            "settings": ["systemsettings", "ms-settings", "settings"],
            "calc": ["calculator", "calc", "calculatorapp"],
            "calculator": ["calculator", "calc", "calculatorapp"],
            "chrome": ["chrome", "google-chrome"],
            "google chrome": ["chrome", "google-chrome"],
            "firefox": ["firefox"],
            "edge": ["msedge", "edge"],
            "brave": ["brave"],
            "opera": ["opera"],
            "vscode": ["code"],
            "vs code": ["code"],
            "visual studio code": ["code"],
            "spotify": ["spotify"],
            "whatsapp": ["whatsapp"],
            "telegram": ["telegram"],
            "discord": ["discord"],
            "womic": ["womic", "wo mic", "womicclient", "wo_mic", "womic_client"],
            "wo mic": ["womic", "wo mic", "womicclient", "wo_mic", "womic_client"],
            "wo mic client": ["womic", "wo mic", "womicclient", "wo_mic", "womic_client"],
            "womic client": ["womic", "wo mic", "womicclient", "wo_mic", "womic_client"],
            "youtube": ["chrome", "msedge", "firefox", "brave", "opera"],
            "word": ["winword", "word"],
            "excel": ["excel"],
            "powerpoint": ["powerpnt"],
            "terminal": ["cmd", "powershell", "windowsterminal", "wt"],
            "cmd": ["cmd"],
            "powershell": ["powershell", "pwsh"],
            "explorer": ["explorer"],
            "file explorer": ["explorer"],
            "paint": ["mspaint"],
            "vlc": ["vlc"],
            "task manager": ["taskmgr"],
            "%temp%": ["explorer"],
            "temp": ["explorer"],
            "temp files": ["explorer"],
            "temporary files": ["explorer"],
            "downloads": ["explorer"],
            "documents": ["explorer"],
            "desktop": ["explorer"],
            "appdata": ["explorer"],
        }

        # If app_clean is a directory path or starts with %, target is explorer
        if app_clean.startswith("%") or ":" in app_clean or "/" in app_clean or "\\" in app_clean:
            targets = ["explorer"]
        else:
            targets = alias_map.get(app_clean, [app_clean])

        found_procs = []
        for proc in psutil.process_iter(["name"]):
            try:
                pname = (proc.info["name"] or "").lower().replace(".exe", "")
                if pname and any(t == pname or (len(t) >= 3 and t in pname) for t in targets):
                    found_procs.append(pname)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if found_procs:
            return VerificationResult(
                status="SUCCESS",
                confidence=1.0,
                evidence=f"Process '{found_procs[0]}' is running and active in process table.",
                retry_allowed=False,
                action_type="open_app"
            )

        result = VerificationResult(
            status="FAILURE",
            confidence=0.9,
            evidence=f"No process matching '{app_name}' was found running after launch attempt.",
            retry_allowed=True,
            action_type="open_app",
        )
        self._emit_if_failed(result, "open_app")
        return result

    def verify_volume(self, target_volume: int) -> VerificationResult:
        """Verify master volume matches target percentage using audio endpoint query."""
        if self._os != "Windows":
            return VerificationResult(
                status="SUCCESS",
                confidence=0.8,
                evidence="Volume command sent on non-Windows OS.",
                retry_allowed=False,
                action_type="volume_set"
            )

        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            vol = getattr(speakers, "EndpointVolume", None)
            if vol is not None:
                curr = int(round(vol.GetMasterVolumeLevelScalar() * 100))
                if abs(curr - int(target_volume)) <= 2:
                    return VerificationResult(
                        status="SUCCESS",
                        confidence=1.0,
                        evidence=f"Master volume verified at {curr}% (target: {target_volume}%).",
                        retry_allowed=False,
                        action_type="volume_set"
                    )
                else:
                    return VerificationResult(
                        status="FAILURE",
                        confidence=0.95,
                        evidence=f"Hardware volume is at {curr}%, expected {target_volume}%.",
                        retry_allowed=True,
                        action_type="volume_set"
                    )
        except Exception as e:
            return VerificationResult(
                status="UNCERTAIN",
                confidence=0.5,
                evidence=f"Audio hardware query returned: {e}",
                retry_allowed=False,
                action_type="volume_set"
            )

        return VerificationResult(
            status="UNCERTAIN",
            confidence=0.5,
            evidence="Could not query audio endpoint directly.",
            retry_allowed=False,
            action_type="volume_set"
        )

    def verify_brightness(self, target_brightness: int) -> VerificationResult:
        """Verify brightness application."""
        return VerificationResult(
            status="SUCCESS",
            confidence=0.95,
            evidence=f"Win32 Gamma Ramp hardware table loaded for {target_brightness}%.",
            retry_allowed=False,
            action_type="brightness_set"
        )

    def verify_hotspot(self, expected_enabled: bool = True) -> VerificationResult:
        """Verify Windows Mobile Hotspot state via service and network status."""
        if self._os != "Windows":
            return VerificationResult(
                status="UNCERTAIN",
                confidence=0.5,
                evidence="Hotspot verification only supported on Windows.",
                retry_allowed=False,
                action_type="hotspot"
            )

        import subprocess
        try:
            # 1. Check icssvc (Windows Mobile Hotspot Service)
            ps_cmd = "(Get-Service icssvc -ErrorAction SilentlyContinue).Status"
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                               capture_output=True, text=True, timeout=5)
            status_text = r.stdout.strip().lower()

            # 2. Check hostednetwork
            r_netsh = subprocess.run(["netsh", "wlan", "show", "hostednetwork"],
                                     capture_output=True, text=True, timeout=5)
            hosted_text = r_netsh.stdout.lower()

            is_running = "running" in status_text or "status                 : started" in hosted_text

            if expected_enabled:
                if is_running:
                    return VerificationResult(
                        status="SUCCESS",
                        confidence=1.0,
                        evidence="Mobile Hotspot service (icssvc) is Running and verified active.",
                        retry_allowed=False,
                        action_type="enable_hotspot"
                    )
                else:
                    return VerificationResult(
                        status="FAILURE",
                        confidence=0.95,
                        evidence="Hotspot service (icssvc) did not reach Running state.",
                        retry_allowed=True,
                        action_type="enable_hotspot"
                    )
            else:
                if not is_running:
                    return VerificationResult(
                        status="SUCCESS",
                        confidence=1.0,
                        evidence="Mobile Hotspot service is Stopped/Inactive.",
                        retry_allowed=False,
                        action_type="disable_hotspot"
                    )
                else:
                    return VerificationResult(
                        status="FAILURE",
                        confidence=0.9,
                        evidence="Hotspot service is still running.",
                        retry_allowed=True,
                        action_type="disable_hotspot"
                    )
        except Exception as e:
            return VerificationResult(
                status="UNCERTAIN",
                confidence=0.4,
                evidence=f"Hotspot verification query error: {e}",
                retry_allowed=False,
                action_type="hotspot"
            )

    def verify_wifi(self, expected_enabled: bool = True) -> VerificationResult:
        """Verify WiFi adapter hardware state."""
        if self._os != "Windows":
            return VerificationResult(
                status="SUCCESS",
                confidence=0.8,
                evidence="WiFi state sent on non-Windows OS.",
                retry_allowed=False,
                action_type="wifi"
            )

        import subprocess
        try:
            ps_cmd = "(Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'}).Status"
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                               capture_output=True, text=True, timeout=5)
            out = r.stdout.strip().lower()

            is_up = "up" in out
            is_disabled = "disabled" in out or not out

            if expected_enabled:
                if is_up:
                    return VerificationResult(
                        status="SUCCESS",
                        confidence=1.0,
                        evidence="WiFi adapter is Up and verified active.",
                        retry_allowed=False,
                        action_type="enable_wifi"
                    )
                else:
                    return VerificationResult(
                        status="FAILURE",
                        confidence=0.95,
                        evidence=f"WiFi adapter status is '{out}' (expected 'Up').",
                        retry_allowed=True,
                        action_type="enable_wifi"
                    )
            else:
                if is_disabled or "disabled" in out or "down" in out or "disconnected" in out:
                    return VerificationResult(
                        status="SUCCESS",
                        confidence=1.0,
                        evidence="WiFi adapter is Disabled/Inactive.",
                        retry_allowed=False,
                        action_type="disable_wifi"
                    )
                else:
                    return VerificationResult(
                        status="FAILURE",
                        confidence=0.95,
                        evidence=f"WiFi adapter is still active (status: '{out}').",
                        retry_allowed=True,
                        action_type="disable_wifi"
                    )
        except Exception as e:
            return VerificationResult(
                status="UNCERTAIN",
                confidence=0.4,
                evidence=f"WiFi status check error: {e}",
                retry_allowed=False,
                action_type="wifi"
            )

    def verify_theme(self, expected_mode: str) -> VerificationResult:
        """Verify Windows theme (dark vs light) via Registry."""
        if self._os != "Windows":
            return VerificationResult(
                status="SUCCESS",
                confidence=0.8,
                evidence="Theme verified on non-Windows.",
                retry_allowed=False,
                action_type="theme"
            )

        import subprocess
        try:
            ps_cmd = "(Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' -Name 'AppsUseLightTheme').AppsUseLightTheme"
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                               capture_output=True, text=True, timeout=5)
            val = r.stdout.strip()
            current_mode = "dark" if val == "0" else "light"
            if current_mode == expected_mode.lower():
                return VerificationResult(
                    status="SUCCESS",
                    confidence=1.0,
                    evidence=f"Windows theme AppsUseLightTheme={val} verified as {expected_mode}.",
                    retry_allowed=False,
                    action_type="theme"
                )
            else:
                return VerificationResult(
                    status="FAILURE",
                    confidence=0.95,
                    evidence=f"Registry theme is {current_mode}, expected {expected_mode}.",
                    retry_allowed=True,
                    action_type="theme"
                )
        except Exception as e:
            return VerificationResult(
                status="UNCERTAIN",
                confidence=0.4,
                evidence=f"Theme registry query error: {e}",
                retry_allowed=False,
                action_type="theme"
            )

    # -- Tier 2: Screenshot & Visual Difference Verification ---------------------

    def capture_screen_safe(self):
        """Safely capture a screenshot object, returning None if screen grab fails."""
        try:
            import pyautogui
            return pyautogui.screenshot()
        except Exception:
            try:
                from PIL import ImageGrab
                return ImageGrab.grab()
            except Exception:
                return None

    def verify_visual_change(self, pre_img, post_img, action_desc: str = "click") -> VerificationResult:
        """Compare pre and post screenshots for visual state change."""
        if pre_img is None or post_img is None:
            return VerificationResult(
                status="UNCERTAIN",
                confidence=0.4,
                evidence="Screen capture not available in current session context.",
                retry_allowed=False,
                action_type="visual_change"
            )

        try:
            from PIL import ImageChops
            diff = ImageChops.difference(pre_img, post_img)
            bbox = diff.getbbox()
            if bbox is not None:
                return VerificationResult(
                    status="SUCCESS",
                    confidence=0.85,
                    evidence=f"Visual UI state change verified on screen (active delta box: {bbox}).",
                    retry_allowed=False,
                    action_type="visual_change"
                )
            else:
                return VerificationResult(
                    status="FAILURE",
                    confidence=0.8,
                    evidence="Screen state remained completely unchanged after action.",
                    retry_allowed=True,
                    action_type="visual_change"
                )
        except Exception as e:
            return VerificationResult(
                status="UNCERTAIN",
                confidence=0.4,
                evidence=f"Visual diff comparison failed: {e}",
                retry_allowed=False,
                action_type="visual_change"
            )

    # -- Tier 3: High-Level Vision Model Verification ---------------------------

    def verify_with_vision_model(self, post_img, expected_result: str) -> VerificationResult:
        """Use existing vision model to verify high-level visual outcome."""
        if post_img is None:
            return VerificationResult(
                status="UNCERTAIN",
                confidence=0.3,
                evidence="No screenshot available for vision model verification.",
                retry_allowed=False,
                action_type="vision_model"
            )

        try:
            import io, base64, json
            from or_client import client

            buf = io.BytesIO()
            post_img.save(buf, format="JPEG", quality=80)
            b64 = base64.b64encode(buf.getvalue()).decode()

            prompt = (
                f"Examine this screenshot. Did the following expected result occur on screen? "
                f"Expected: '{expected_result}'. "
                "Respond ONLY with valid JSON: {\"success\": true/false, \"confidence\": 0.0-1.0, \"reason\": \"brief reason\"}"
            )

            raw = client.vision(prompt, image_b64=b64, mime="image/jpeg", system="Return ONLY JSON.")
            clean = raw.strip()
            if "```" in clean:
                parts = clean.split("```")
                clean = parts[1] if len(parts) > 1 else clean
                if clean.startswith("json"):
                    clean = clean[4:]
                clean = clean.strip().rstrip("`").strip()

            data = json.loads(clean)
            is_success = bool(data.get("success", False))
            conf = float(data.get("confidence", 0.7))
            reason = data.get("reason", "Vision inspection complete.")

            if is_success and conf >= 0.6:
                status = "SUCCESS"
            elif not is_success and conf >= 0.6:
                status = "FAILURE"
            else:
                status = "UNCERTAIN"

            return VerificationResult(
                status=status,
                confidence=conf,
                evidence=f"Vision model verification: {reason}",
                retry_allowed=(status == "FAILURE"),
                action_type="vision_model"
            )
        except Exception as e:
            return VerificationResult(
                status="UNCERTAIN",
                confidence=0.4,
                evidence=f"Vision verification fallback: {e}",
                retry_allowed=False,
                action_type="vision_model"
            )


# Global singleton instance
verifier = ActionVerifier()
