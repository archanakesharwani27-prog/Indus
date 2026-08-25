# core/vision_manager.py
"""
INDUS Core Vision Manager & Visual Interaction Orchestrator
===========================================================
Powers closed-loop computer vision, multimodal UI grounding, and automated
GUI interaction (click, type, scroll, drag) with state change verification.
"""

from __future__ import annotations
import base64
import io
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image

logger = logging.getLogger("IndusVisionManager")


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

CLICK_CONFIDENCE_THRESHOLD = 0.60

GEMINI_VISION_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest",
]


@dataclass
class GroundingResult:
    found: bool = False
    target: str = ""
    center_x: int = -1
    center_y: int = -1
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # left, top, width, height
    confidence: float = 0.0
    element_type: str = "unknown"
    description: str = ""
    is_ambiguous: bool = False
    candidate_count: int = 0
    ambiguity_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "target": self.target,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "bbox": list(self.bbox),
            "confidence": self.confidence,
            "element_type": self.element_type,
            "description": self.description,
            "is_ambiguous": self.is_ambiguous,
            "candidate_count": self.candidate_count,
            "ambiguity_reason": self.ambiguity_reason,
        }


@dataclass
class VisualActionResult:
    success: bool
    action_type: str
    target: str
    coordinates: Tuple[int, int]
    message: str
    verified: bool = False
    verification_details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action_type": self.action_type,
            "target": self.target,
            "coordinates": self.coordinates,
            "message": self.message,
            "verified": self.verified,
            "verification_details": self.verification_details,
        }


class VisionManager:
    """Central manager for vision perception and visual interaction in INDUS."""

    def __init__(self):
        self._last_screenshot: Optional[Image.Image] = None
        self._last_grounding: Optional[GroundingResult] = None

    def _get_gemini_key(self) -> str:
        try:
            from core.secure_storage import load_secure_json
            data = load_secure_json(CONFIG_PATH)
            return data.get("gemini_api_key", "").strip()
        except Exception:
            return ""

    # ── Screen Capture & Compression ─────────────────────────────────────────

    def capture(self) -> Tuple[Image.Image, int, int]:
        """Capture current screen safely using multiple OS fallbacks."""
        # 1. mss (fast multi-monitor)
        try:
            import mss
            with mss.MSS() as sct:
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                shot = sct.grab(mon)
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                self._last_screenshot = img
                return img, img.width, img.height
        except Exception:
            pass

        # 2. PIL ImageGrab
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=False)
            if img:
                img_rgb = img.convert("RGB")
                self._last_screenshot = img_rgb
                return img_rgb, img_rgb.width, img_rgb.height
        except Exception:
            pass

        # 3. PyAutoGUI
        try:
            import pyautogui
            w, h = pyautogui.size()
            img = pyautogui.screenshot()
            if img:
                img_rgb = img.convert("RGB")
                self._last_screenshot = img_rgb
                return img_rgb, w, h
        except Exception:
            pass

        # 4. Headless test canvas fallback
        fallback = Image.new("RGB", (1920, 1080), color=(20, 24, 32))
        self._last_screenshot = fallback
        return fallback, 1920, 1080

    def compress_image(self, img: Image.Image, max_dim: int = 1280, quality: int = 75) -> Tuple[str, str]:
        """Downscale and compress image for low-latency vision API transmission."""
        copy_img = img.copy()
        if max(copy_img.size) > max_dim:
            copy_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        copy_img.save(buf, format="JPEG", quality=quality, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return b64, "image/jpeg"

    # ── Tier 1: Local OCR Extraction ─────────────────────────────────────────

    def extract_ocr(self, img: Image.Image) -> List[Dict[str, Any]]:
        """Extract visible text tokens and bounding boxes using pytesseract."""
        from actions.vision_engine import TESSERACT_EXE
        if not TESSERACT_EXE:
            return []
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

            elements = []
            n_boxes = len(data["text"])
            for i in range(n_boxes):
                text = str(data["text"][i]).strip()
                conf = float(data["conf"][i]) if "conf" in data else 0.0
                if text and conf > 30.0:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    elements.append({
                        "text": text,
                        "x": x,
                        "y": y,
                        "w": w,
                        "h": h,
                        "cx": x + w // 2,
                        "cy": y + h // 2,
                        "conf": conf / 100.0,
                    })
            return elements
        except Exception as e:
            logger.debug(f"[VisionManager] OCR error: {e}")
            return []

    # ── Multimodal Grounding Cascade (Tiers 0 - 3) ───────────────────────────

    def ground(
        self,
        target_description: str,
        context: str = "",
        img: Optional[Image.Image] = None,
        player=None
    ) -> GroundingResult:
        """
        Locates UI element on screen using multi-tier perception cascade.
        """
        from core.cancellation import cancellation_manager

        if cancellation_manager.is_cancelled():
            return GroundingResult(found=False, description="Operation cancelled by user.")

        if img is None:
            img, screen_w, screen_h = self.capture()
        else:
            screen_w, screen_h = img.width, img.height

        if player:
            player.write_log(f"[Vision] Grounding UI target: '{target_description}' on {screen_w}x{screen_h}")

        # Tier 1: Fast Local OCR keyword matching
        ocr_elements = self.extract_ocr(img)
        matches = []
        if target_description and ocr_elements:
            kw = target_description.strip().lower()
            for el in ocr_elements:
                t = el["text"].lower()
                if kw in t or t in kw:
                    matches.append(el)

        # Tier 3: Multimodal Vision Model Grounding (Gemini 2.5 Flash)
        b64_image, mime_type = self.compress_image(img, max_dim=1280)
        prompt = (
            f"You are a computer vision UI grounding specialist.\n"
            f"Analyze this {screen_w}x{screen_h} screenshot and find the UI element corresponding to: '{target_description}'.\n"
            f"Context/Surroundings: {context if context else 'None'}\n\n"
            "Return ONLY a JSON object with this exact schema:\n"
            "{\n"
            '  "found": true/false,\n'
            '  "element_type": "button" | "input" | "icon" | "link" | "tab" | "checkbox" | "menu" | "unknown",\n'
            '  "center_x": <pixel integer horizontal coordinate 0 to ' + str(screen_w) + '>,\n'
            '  "center_y": <pixel integer vertical coordinate 0 to ' + str(screen_h) + '>,\n'
            '  "bbox": [<left>, <top>, <width>, <height>],\n'
            '  "confidence": <float 0.0 to 1.0>,\n'
            '  "description": "<concise description of where it is and what it looks like>",\n'
            '  "is_ambiguous": true/false,\n'
            '  "candidate_count": <integer number of matching elements on screen>,\n'
            '  "ambiguity_reason": "<explanation if multiple matches or unclear>"\n'
            "}\n"
        )

        result_json = None
        api_key = self._get_gemini_key()
        if api_key:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
                raw_bytes = base64.b64decode(b64_image)

                for model_name in GEMINI_VISION_CANDIDATES:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[
                                types.Part.from_bytes(data=raw_bytes, mime_type=mime_type),
                                prompt,
                            ],
                            config={"temperature": 0.1, "response_mime_type": "application/json"},
                        )
                        text = response.text.strip()
                        result_json = json.loads(text)
                        if result_json:
                            break
                    except Exception as model_err:
                        logger.debug(f"[VisionManager] {model_name} attempt error: {model_err}")
            except Exception as e:
                logger.debug(f"[VisionManager] Gemini direct grounding error: {e}")

        # Fallback to or_client
        if not result_json:
            try:
                from or_client import client as or_c
                raw_text = or_c.vision(prompt, image_b64=b64_image, mime=mime_type)
                clean = raw_text.strip()
                if "```" in clean:
                    clean = re.sub(r"^```(?:json)?\s*", "", clean)
                    clean = re.sub(r"\s*```$", "", clean)
                result_json = json.loads(clean)
            except Exception as e:
                logger.debug(f"[VisionManager] or_client vision fallback error: {e}")

        # Integrate OCR matches if model found nothing or for exact text verification
        if not result_json or not result_json.get("found"):
            if matches:
                best = matches[0]
                res = GroundingResult(
                    found=True,
                    target=target_description,
                    center_x=best["cx"],
                    center_y=best["cy"],
                    bbox=(best["x"], best["y"], best["w"], best["h"]),
                    confidence=min(0.85, best["conf"]),
                    element_type="text_element",
                    description=f"OCR detected '{best['text']}'",
                    is_ambiguous=len(matches) > 1,
                    candidate_count=len(matches),
                    ambiguity_reason="Multiple OCR matches on screen" if len(matches) > 1 else "",
                )
                self._last_grounding = res
                return res

            res = GroundingResult(
                found=False,
                target=target_description,
                confidence=0.0,
                description=f"Target '{target_description}' was not found on screen.",
            )
            self._last_grounding = res
            return res

        # Validate bounds
        cx = int(result_json.get("center_x", -1))
        cy = int(result_json.get("center_y", -1))
        bbox_list = result_json.get("bbox") or [0, 0, 0, 0]
        bbox = (bbox_list[0], bbox_list[1], bbox_list[2], bbox_list[3]) if len(bbox_list) >= 4 else (0, 0, 0, 0)

        is_found = result_json.get("found", False) and (5 <= cx <= screen_w - 5 and 5 <= cy <= screen_h - 5)
        conf = float(result_json.get("confidence", 0.8)) if is_found else 0.0

        is_ambiguous = result_json.get("is_ambiguous", False) or len(matches) > 1
        cand_count = max(result_json.get("candidate_count", 1), len(matches))

        res = GroundingResult(
            found=is_found,
            target=target_description,
            center_x=cx if is_found else -1,
            center_y=cy if is_found else -1,
            bbox=bbox,
            confidence=conf,
            element_type=result_json.get("element_type", "unknown"),
            description=result_json.get("description", target_description),
            is_ambiguous=is_ambiguous,
            candidate_count=cand_count,
            ambiguity_reason=result_json.get("ambiguity_reason", ""),
        )
        self._last_grounding = res
        return res

    # ── Visual Action Primitives ─────────────────────────────────────────────

    def click(
        self,
        target: str,
        context: str = "",
        click_type: str = "single",
        player=None
    ) -> VisualActionResult:
        """Locates element visually, clicks it, and verifies post-action state."""
        from core.cancellation import cancellation_manager
        from actions.action_verifier import ActionVerifier

        if cancellation_manager.is_cancelled():
            return VisualActionResult(False, "click", target, (-1, -1), "Click cancelled by user.")

        if not target:
            return VisualActionResult(False, "click", "", (-1, -1), "Target UI element is required.")

        grounding = self.ground(target, context=context, player=player)
        if cancellation_manager.is_cancelled():
            return VisualActionResult(False, "click", target, (-1, -1), "Operation cancelled by user.")

        if not grounding.found:
            return VisualActionResult(
                False, "click", target, (-1, -1),
                f"Target '{target}' not found on screen. ({grounding.description})"
            )

        if grounding.confidence < CLICK_CONFIDENCE_THRESHOLD:
            return VisualActionResult(
                False, "click", target, (grounding.center_x, grounding.center_y),
                f"Confidence too low ({grounding.confidence:.2f} < {CLICK_CONFIDENCE_THRESHOLD:.2f}) for '{target}'."
            )

        if grounding.is_ambiguous:
            return VisualActionResult(
                False, "click", target, (grounding.center_x, grounding.center_y),
                f"Target '{target}' is ambiguous ({grounding.candidate_count} matches). {grounding.ambiguity_reason}"
            )

        cx, cy = grounding.center_x, grounding.center_y
        verifier = ActionVerifier(player_ui=player)
        pre_snap = verifier.capture_state_snapshot("vision_click", {"target": target})

        try:
            import pyautogui
            pyautogui.moveTo(cx, cy, duration=0.2)
            time.sleep(0.05)

            if click_type == "double":
                pyautogui.doubleClick(cx, cy)
            elif click_type == "right":
                pyautogui.rightClick(cx, cy)
            else:
                pyautogui.click(cx, cy)

            time.sleep(0.35)
        except Exception as e:
            return VisualActionResult(False, "click", target, (cx, cy), f"Click execution failed: {e}")

        post_snap = verifier.capture_state_snapshot("vision_click", {"target": target})
        verification = verifier.verify_action_success("vision_click", pre_snap, post_snap, expected_target=target)

        return VisualActionResult(
            success=True,
            action_type="click",
            target=target,
            coordinates=(cx, cy),
            message=f"Clicked '{target}' at ({cx}, {cy}).",
            verified=verification.verified,
            verification_details=verification.details,
        )

    def type_text(
        self,
        target: str,
        text: str,
        press_enter: bool = True,
        clear_first: bool = True,
        context: str = "",
        player=None
    ) -> VisualActionResult:
        """
        Visually locates input field/search bar, focuses it, clears existing text,
        types new text, and optionally presses Enter.
        """
        from core.cancellation import cancellation_manager
        from actions.action_verifier import ActionVerifier

        if cancellation_manager.is_cancelled():
            return VisualActionResult(False, "type", target, (-1, -1), "Typing cancelled by user.")

        if not text:
            return VisualActionResult(False, "type", target, (-1, -1), "No text provided to type.")

        # If a specific visual target is provided, locate and click to focus
        cx, cy = -1, -1
        if target:
            grounding = self.ground(target, context=context, player=player)
            if grounding.found and grounding.confidence >= 0.50:
                cx, cy = grounding.center_x, grounding.center_y
                try:
                    import pyautogui
                    pyautogui.click(cx, cy)
                    time.sleep(0.2)
                except Exception:
                    pass

        verifier = ActionVerifier(player_ui=player)
        pre_snap = verifier.capture_state_snapshot("vision_type", {"target": target, "text": text})

        try:
            import pyautogui
            import pyperclip

            if clear_first:
                # Select All -> Backspace
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.05)
                pyautogui.press("backspace")
                time.sleep(0.05)

            # Paste text via clipboard for fast & accurate Unicode handling
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.15)

            if press_enter:
                pyautogui.press("enter")
                time.sleep(0.4)

        except Exception as e:
            return VisualActionResult(False, "type", target, (cx, cy), f"Typing execution failed: {e}")

        post_snap = verifier.capture_state_snapshot("vision_type", {"target": target, "text": text})
        verification = verifier.verify_action_success("vision_type", pre_snap, post_snap, expected_target=target)

        return VisualActionResult(
            success=True,
            action_type="type",
            target=target,
            coordinates=(cx, cy),
            message=f"Typed '{text}' into '{target or 'active field'}'" + (" (with Enter)" if press_enter else ""),
            verified=verification.verified,
            verification_details=verification.details,
        )

    def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        target: Optional[str] = None,
        player=None
    ) -> VisualActionResult:
        """Scrolls target container or active screen."""
        from actions.action_verifier import ActionVerifier

        cx, cy = -1, -1
        if target:
            grounding = self.ground(target, player=player)
            if grounding.found:
                cx, cy = grounding.center_x, grounding.center_y
                try:
                    import pyautogui
                    pyautogui.moveTo(cx, cy, duration=0.15)
                except Exception:
                    pass

        verifier = ActionVerifier(player_ui=player)
        pre_snap = verifier.capture_state_snapshot("vision_scroll", {"direction": direction})

        try:
            import pyautogui
            scroll_amt = -abs(int(amount or 300)) if direction.lower() == "down" else abs(int(amount or 300))
            pyautogui.scroll(scroll_amt)
            time.sleep(0.3)
        except Exception as e:
            return VisualActionResult(False, "scroll", target or "", (cx, cy), f"Scroll failed: {e}")

        post_snap = verifier.capture_state_snapshot("vision_scroll", {"direction": direction})
        verification = verifier.verify_action_success("vision_scroll", pre_snap, post_snap)

        return VisualActionResult(
            success=True,
            action_type="scroll",
            target=target or "",
            coordinates=(cx, cy),
            message=f"Scrolled {direction} by {abs(amount)} units.",
            verified=verification.verified,
            verification_details=verification.details,
        )

    def inspect_screen(self, query: str = "What is visible on my screen?", player=None) -> str:
        """Visual Question Answering on current screen."""
        from actions.vision_engine import screen_understand
        return screen_understand(query=query, player=player)


# Global singleton instance
vision_manager = VisionManager()
