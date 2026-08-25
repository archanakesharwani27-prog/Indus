# actions/vision_engine.py
"""
INDUS Advanced Vision & UI Screen Grounding Engine
Provides:
1. High-accuracy screen capture with DPI and multi-monitor awareness
2. Local OCR text & bounding box extraction (pytesseract)
3. Gemini 2.5 Multimodal UI Grounding (buttons, inputs, toggles, dialogs)
4. Visual Question Answering (VQA)
5. Ambiguity & Low-Confidence rejection guardrails
6. Closed-loop vision-guided computer control with ActionVerifier integration
7. Cooperative cancellation via CancellationManager
"""

import base64
import io
import json
import logging
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

logger = logging.getLogger("IndusVision")

# Base directory & config loading
def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

# Minimum confidence threshold required to execute automated mouse clicks
CLICK_CONFIDENCE_THRESHOLD = 0.60

GEMINI_VISION_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest",
]


# Configure pytesseract path
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if shutil.which("tesseract"):
    TESSERACT_EXE = shutil.which("tesseract")
elif os.path.exists(TESSERACT_CMD):
    TESSERACT_EXE = TESSERACT_CMD
else:
    TESSERACT_EXE = None


def _get_api_key() -> str:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("gemini_api_key", "").strip()
    except Exception:
        return ""


# --- 1. Reliable Screen Capture Layer ---------------------------------------

def capture_screen() -> Tuple[Image.Image, int, int]:
    """
    Capture current screen safely using multiple fallbacks.
    Returns: (PIL.Image in RGB, screen_width, screen_height)
    """
    # 1. Try mss (fastest and handles multi-monitor)
    try:
        import mss
        with mss.MSS() as sct:
            mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            return img, img.width, img.height
    except Exception as e:
        logger.debug(f"[VisionEngine] mss capture failed: {e}")

    # 2. Try PIL ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=False)
        if img:
            return img.convert("RGB"), img.width, img.height
    except Exception as e:
        logger.debug(f"[VisionEngine] ImageGrab capture failed: {e}")

    # 3. Try pyautogui
    try:
        import pyautogui
        w, h = pyautogui.size()
        img = pyautogui.screenshot()
        if img:
            return img.convert("RGB"), w, h
    except Exception as e:
        logger.debug(f"[VisionEngine] pyautogui capture failed: {e}")

    # 4. Fallback test canvas for headless / lock screen environments
    fallback_w, fallback_h = 1920, 1080
    fallback_img = Image.new("RGB", (fallback_w, fallback_h), color=(20, 24, 32))
    return fallback_img, fallback_w, fallback_h


def image_to_base64(img: Image.Image, max_dim: int = 1280, quality: int = 75) -> Tuple[str, str]:
    """
    Downscale and compress image for low-latency vision API transmission.
    Returns: (base64_str, mime_type)
    """
    copy_img = img.copy()
    if max(copy_img.size) > max_dim:
        copy_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    copy_img.save(buf, format="JPEG", quality=quality, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return b64, "image/jpeg"


# --- 2. OCR Text Extraction Layer ------------------------------------------

def extract_ocr_elements(img: Image.Image) -> List[Dict[str, Any]]:
    """
    Extract visible text tokens and bounding boxes from image using pytesseract.
    Returns list of dicts: {'text', 'x', 'y', 'w', 'h', 'cx', 'cy', 'conf'}
    """
    if not TESSERACT_EXE:
        return []

    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        elements = []
        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
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
        logger.warning(f"[VisionEngine] OCR extraction error: {e}")
        return []


def find_ocr_keyword(keyword: str, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find OCR elements matching keyword or phrase with case-insensitive boundary match."""
    if not keyword or not elements:
        return []
    kw = keyword.strip().lower()
    matches = []
    for el in elements:
        t = el["text"].lower()
        if kw in t or t in kw:
            matches.append(el)
    return matches


# --- 3. Multimodal UI Grounding (Gemini 2.5 + OpenRouter Fallback) --------

def ground_ui_element(
    target_description: str,
    context: str = "",
    img: Optional[Image.Image] = None,
    player=None,
) -> Dict[str, Any]:
    """
    Ground a UI element from target description on the screen.
    Returns structured dict with coordinates, confidence, ambiguity, and description.
    """
    from core.cancellation import cancellation_manager

    if cancellation_manager.is_cancelled():
        return {
            "found": False,
            "error": "Operation cancelled by user.",
            "target": target_description,
            "confidence": 0.0,
        }

    if img is None:
        img, screen_w, screen_h = capture_screen()
    else:
        screen_w, screen_h = img.width, img.height

    if player:
        player.write_log(f"[Vision] Grounding target: '{target_description}' on {screen_w}x{screen_h} screen")

    # Step 1: Fast local OCR matching for exact text buttons
    ocr_elements = extract_ocr_elements(img)
    ocr_matches = find_ocr_keyword(target_description, ocr_elements)

    # Step 2: Query Multimodal Vision Model (Gemini 2.5 Flash)
    b64_image, mime_type = image_to_base64(img, max_dim=1280)

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

    # Try Gemini Vision Models directly
    result_json = None
    api_key = _get_api_key()
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
                    logger.debug(f"[VisionEngine] {model_name} grounding attempt error: {model_err}")
        except Exception as e:
            logger.warning(f"[VisionEngine] Gemini direct vision grounding failed: {e}")


    # Fallback to or_client if needed
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
            logger.warning(f"[VisionEngine] or_client fallback grounding failed: {e}")

    # Step 3: Combine with OCR coordinates if valid and enhance accuracy
    if not result_json or not result_json.get("found"):
        if ocr_matches:
            # Single exact OCR match fallback
            best_ocr = ocr_matches[0]
            return {
                "found": True,
                "target": target_description,
                "element_type": "text_element",
                "center_x": best_ocr["cx"],
                "center_y": best_ocr["cy"],
                "bbox": [best_ocr["x"], best_ocr["y"], best_ocr["w"], best_ocr["h"]],
                "confidence": min(0.85, best_ocr["conf"]),
                "description": f"OCR detected text '{best_ocr['text']}'",
                "is_ambiguous": len(ocr_matches) > 1,
                "candidate_count": len(ocr_matches),
                "ambiguity_reason": "Multiple OCR matches on screen" if len(ocr_matches) > 1 else "",
            }
        return {
            "found": False,
            "target": target_description,
            "confidence": 0.0,
            "description": f"Element '{target_description}' was not found on screen.",
            "is_ambiguous": False,
            "candidate_count": 0,
        }

    # Bounds check coordinates to ensure they are on screen
    cx = int(result_json.get("center_x", -1))
    cy = int(result_json.get("center_y", -1))
    margin = 5
    if not (margin <= cx <= screen_w - margin and margin <= cy <= screen_h - margin):
        result_json["found"] = False
        result_json["confidence"] = 0.0
        result_json["description"] = f"Calculated coordinates ({cx}, {cy}) outside screen bounds ({screen_w}x{screen_h})."

    # Ambiguity check
    if len(ocr_matches) > 1 and not result_json.get("is_ambiguous"):
        result_json["candidate_count"] = max(result_json.get("candidate_count", 1), len(ocr_matches))
        if result_json["candidate_count"] > 1 and not context:
            result_json["is_ambiguous"] = True
            result_json["ambiguity_reason"] = f"Multiple ({result_json['candidate_count']}) similar targets detected on screen."

    return result_json


# --- 4. Visual Question Answering (VQA / Screen Understand) ----------------

def screen_understand(query: str = "What is currently visible on my screen?", player=None) -> str:
    """
    Answers questions about the screen without performing any clicks.
    Examples:
    - 'What application is open?'
    - 'What error is showing?'
    - 'Is Bluetooth toggle active?'
    - 'Summarize what is on the page.'
    """
    from core.cancellation import cancellation_manager

    if cancellation_manager.is_cancelled():
        return "Screen understanding was cancelled by user."

    if player:
        player.write_log(f"[Vision] Understanding: '{query}'")

    img, w, h = capture_screen()
    b64_image, mime_type = image_to_base64(img, max_dim=1280)

    prompt = (
        f"You are INDUS, an intelligent AI assistant analyzing the user's computer screen ({w}x{h} resolution).\n"
        f"User query: '{query}'\n\n"
        "Instructions:\n"
        "1. Give a crisp, direct, and factual answer in 2-3 natural sentences.\n"
        "2. Focus specifically on what the user asked about (e.g. open apps, errors, status, text, buttons).\n"
        "3. Do NOT make up elements. If an application or error is not visible, say so clearly.\n"
        "4. Respond naturally in Hinglish/English without technical metadata or markdown code blocks."
    )

    api_key = _get_api_key()
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
                        config={"temperature": 0.2, "max_output_tokens": 400},
                    )
                    text = response.text.strip()
                    if text:
                        return text
                except Exception as m_err:
                    logger.debug(f"[VisionEngine] {model_name} VQA error: {m_err}")
        except Exception as e:
            logger.warning(f"[VisionEngine] Gemini direct VQA error: {e}")


    # Fallback to OpenRouter / Nemotron
    try:
        from or_client import client as or_c
        return or_c.vision(prompt, image_b64=b64_image, mime=mime_type, max_tokens=300)
    except Exception as e:
        return f"Unable to analyze screen: {e}"


# --- 5. Vision-Guided Safe Computer Control -------------------------------

def vision_click(target: str, context: str = "", player=None) -> str:
    """
    Locates a target UI element visually, checks safety/confidence, clicks it,
    and runs ActionVerifier to verify that the expected screen change occurred.
    """
    from core.cancellation import cancellation_manager
    from core.security_vault import security_vault
    from actions.action_verifier import ActionVerifier

    if cancellation_manager.is_cancelled():
        return "Click cancelled by user."

    if not target:
        return "Target UI element name or description is required."

    if player:
        player.write_log(f"[Vision] Locating and clicking: '{target}'")

    # Step 1: Security Policy Check on target action
    sec_decision = security_vault.evaluate_action(
        action_name="vision_click",
        parameters={"target": target, "context": context},
    )
    if not sec_decision.allowed:
        return f"Security Policy Blocked: {sec_decision.reason}"

    # Step 2: Ground UI target
    grounding = ground_ui_element(target, context=context, player=player)

    if cancellation_manager.is_cancelled():
        return "Operation cancelled by user."

    if not grounding.get("found"):
        return f"Target '{target}' was not found on screen. ({grounding.get('description', '')})"

    # Step 3: Confidence & Ambiguity Evaluation
    confidence = float(grounding.get("confidence", 0.0))
    if confidence < CLICK_CONFIDENCE_THRESHOLD:
        return (
            f"Cannot click '{target}': Confidence is too low ({confidence:.2f} < {CLICK_CONFIDENCE_THRESHOLD:.2f}). "
            f"Description: {grounding.get('description', 'Unclear visual target')}."
        )

    if grounding.get("is_ambiguous"):
        count = grounding.get("candidate_count", "multiple")
        reason = grounding.get("ambiguity_reason", "Multiple matching targets visible.")
        return f"Target '{target}' is ambiguous ({count} found). {reason} Please specify which one (e.g. 'top right {target}')."

    cx = grounding["center_x"]
    cy = grounding["center_y"]
    desc = grounding.get("description", target)

    # Step 4: Pre-action snapshot for ActionVerifier
    verifier = ActionVerifier(player_ui=player)
    pre_snap = verifier.capture_state_snapshot("vision_click", {"target": target})

    if cancellation_manager.is_cancelled():
        return "Operation cancelled before click."

    # Step 5: Perform physical click via PyAutoGUI
    try:
        import pyautogui
        pyautogui.moveTo(cx, cy, duration=0.2)
        time.sleep(0.05)
        pyautogui.click(cx, cy)
        time.sleep(0.35)
    except Exception as e:
        return f"Failed to click coordinates ({cx}, {cy}): {e}"

    if cancellation_manager.is_cancelled():
        return "Operation cancelled after click."

    # Step 6: Post-action verification with ActionVerifier
    post_snap = verifier.capture_state_snapshot("vision_click", {"target": target})
    verification = verifier.verify_action_success("vision_click", pre_snap, post_snap, expected_target=target)

    status_icon = "Verified" if verification.verified else "Executed"
    return f"[{status_icon}] Clicked '{target}' at ({cx}, {cy}) [{desc}]. Verification: {verification.details}"


def vision_type(
    target: str = "",
    text: str = "",
    press_enter: bool = True,
    clear_first: bool = True,
    context: str = "",
    player=None,
) -> str:
    """
    Visually locates an input field or search bar, focuses it, and types text.
    """
    from core.vision_manager import vision_manager
    res = vision_manager.type_text(
        target=target,
        text=text,
        press_enter=press_enter,
        clear_first=clear_first,
        context=context,
        player=player,
    )
    status_icon = "Verified" if res.verified else ("Success" if res.success else "Failed")
    return f"[{status_icon}] {res.message}"


def vision_scroll(
    direction: str = "down",
    amount: int = 300,
    target: Optional[str] = None,
    player=None,
) -> str:
    """
    Scrolls on screen or within a visually grounded container.
    """
    from core.vision_manager import vision_manager
    res = vision_manager.scroll(
        direction=direction,
        amount=amount,
        target=target,
        player=player,
    )
    status_icon = "Verified" if res.verified else ("Success" if res.success else "Failed")
    return f"[{status_icon}] {res.message}"


def vision_engine(parameters: dict, player=None) -> str:
    """
    Unified Vision Tool Dispatcher for Gemini Tool Routing.
    Supports: click, type, scroll, inspect, locate, ocr.
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if action in ("click", "click_element", "tap"):
        return vision_click(
            target=params.get("target", ""),
            context=params.get("context", ""),
            player=player,
        )
    elif action in ("type", "write", "type_text", "search"):
        return vision_type(
            target=params.get("target", ""),
            text=params.get("text", "") or params.get("query", ""),
            press_enter=params.get("press_enter", True),
            clear_first=params.get("clear_first", True),
            context=params.get("context", ""),
            player=player,
        )
    elif action in ("scroll", "scroll_down", "scroll_up"):
        return vision_scroll(
            direction=params.get("direction", "down"),
            amount=params.get("amount", 300),
            target=params.get("target"),
            player=player,
        )
    elif action in ("inspect", "understand", "vqa", "describe", "explain"):
        return screen_understand(
            query=params.get("query", "") or params.get("description", "What is currently on screen?"),
            player=player,
        )
    elif action in ("locate", "ground", "find"):
        from core.vision_manager import vision_manager
        res = vision_manager.ground(
            target_description=params.get("target", ""),
            context=params.get("context", ""),
            player=player,
        )
        return json.dumps(res.to_dict())
    elif action in ("ocr", "read", "extract_text"):
        from core.vision_manager import vision_manager
        img, _, _ = capture_screen()
        tokens = vision_manager.extract_ocr(img)
        texts = [t["text"] for t in tokens]
        return f"Visible OCR text tokens ({len(texts)}): {' '.join(texts[:50])}"

    # Default fallback: inspect screen or locate target
    if "target" in params:
        return vision_click(target=params["target"], context=params.get("context", ""), player=player)
    return screen_understand(query=params.get("query", "What is on screen?"), player=player)
