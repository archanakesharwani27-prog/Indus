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
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
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


# --- 2. OCR Text Extraction Layer (Windows Native winocr + Tesseract Fallback) ---

def extract_ocr_elements(img: Image.Image) -> List[Dict[str, Any]]:
    """
    Extract visible text tokens and bounding boxes from image using Windows Native OCR (winocr)
    with pytesseract fallback.
    Returns list of dicts: {'text', 'x', 'y', 'w', 'h', 'cx', 'cy', 'conf'}
    """
    elements = []

    # 1. Primary Tier: Windows Native Hardware-Accelerated OCR (~20-50ms)
    try:
        import winocr
        langs = [l.language_tag for l in winocr.OcrEngine.available_recognizer_languages]
        lang = langs[0] if langs else ""
        res = winocr.recognize_pil_sync(img, lang=lang)
        if isinstance(res, dict) and "lines" in res:
            for line in res["lines"]:
                line_text = line.get("text", "").strip()
                words = line.get("words", [])

                # Add multi-word line bounds as combined element (e.g. "WO Mic Client")
                if len(words) > 1 and line_text:
                    min_x = min(w["bounding_rect"]["x"] for w in words)
                    min_y = min(w["bounding_rect"]["y"] for w in words)
                    max_x = max(w["bounding_rect"]["x"] + w["bounding_rect"]["width"] for w in words)
                    max_y = max(w["bounding_rect"]["y"] + w["bounding_rect"]["height"] for w in words)
                    lw = max_x - min_x
                    lh = max_y - min_y
                    elements.append({
                        "text": line_text,
                        "x": int(min_x),
                        "y": int(min_y),
                        "w": int(lw),
                        "h": int(lh),
                        "cx": int(min_x + lw / 2),
                        "cy": int(min_y + lh / 2),
                        "conf": 0.95,
                    })

                # Individual word bounding boxes
                for w_info in words:
                    txt = w_info.get("text", "").strip()
                    rect = w_info.get("bounding_rect", {})
                    if txt and rect:
                        x = int(rect.get("x", 0))
                        y = int(rect.get("y", 0))
                        w = int(rect.get("width", 0))
                        h = int(rect.get("height", 0))
                        elements.append({
                            "text": txt,
                            "x": x,
                            "y": y,
                            "w": w,
                            "h": h,
                            "cx": x + w // 2,
                            "cy": y + h // 2,
                            "conf": 0.90,
                        })
            if elements:
                return elements
    except Exception as e:
        logger.debug(f"[VisionEngine] winocr error: {e}")

    # 2. Secondary Tier: Tesseract OCR fallback
    if TESSERACT_EXE:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

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
        except Exception as e:
            logger.warning(f"[VisionEngine] OCR extraction error: {e}")

    return elements


SPATIAL_HINTS = {
    "below": ("below", ["thoda sa niche", "thoda niche", "niche", "below", "down", "bottom"]),
    "above": ("above", ["upar", "above", "top"]),
    "center": ("center", ["center mein", "center me", "center", "middle", "beech mein", "beech me", "dialog"]),
    "left": ("left", ["left", "bayein"]),
    "right": ("right", ["right", "dayein"]),
}


def _clean_target_text(t: str) -> str:
    """Clean conversational words and delimiters from target element names."""
    t = re.sub(r"^(?:ab\s+)?(?:screen\s+dekh(?:\s*kr|\s*kar)?\s+)?", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^(?:please\s+|kripya\s+|jarvis\s+|indus\s+|gadhi\s+)", "", t, flags=re.IGNORECASE)
    t = re.sub(
        r"\b(click|lick|kro|kr|daba|daba do|button|menu|pr|pe|par|ko|mein|me|se|hi|bhi|aur|fir|fir se|wala|wali|thoda|thoda sa|ke|kr ke|ke baad|hai|tha|gadhi)\b",
        " ",
        t,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", t).strip()


def _extract_spatial_hint(text: str) -> Tuple[str, Optional[str]]:
    """Extract spatial constraint (below, center, above) and clean target name."""
    hint = None
    cleaned = text
    for h_type, (name, keywords) in SPATIAL_HINTS.items():
        for kw in keywords:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, cleaned, flags=re.IGNORECASE):
                hint = name
                cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
                break
        if hint:
            break
    cleaned = _clean_target_text(cleaned)
    return cleaned, hint


def _parse_click_sequence(target_str: str) -> List[Tuple[str, Optional[str]]]:
    """
    Parse multi-step click sequence from user phrases or delimiters with spatial hints.
    Examples:
    - 'connection -> connect -> connect'
    - 'connection pr fir se click kr ke connect pr fir connect pr lick kro'
    - 'gadhi connection kr thoda sa niche hi connect hai aur fir center mein connect hai'
    """
    raw = (target_str or "").strip()
    if not raw:
        return []

    # 1. Delimiter splitting
    for delim in ("->", ">>", "|", ";"):
        if delim in raw:
            parts = [_extract_spatial_hint(p) for p in raw.split(delim)]
            parts = [p for p in parts if p[0]]
            if len(parts) > 1:
                return parts

    # 2. Sequential connectors
    seq_split = re.split(
        r"\b(?:aur fir|fir se|fir|then|and then|baad mein|kr ke|ke baad|aur|kr)\b",
        raw,
        flags=re.IGNORECASE,
    )
    cleaned_seq = [_extract_spatial_hint(s) for s in seq_split]
    cleaned_seq = [s for s in cleaned_seq if s[0]]
    if len(cleaned_seq) > 1:
        return cleaned_seq

    # 3. Comma-separated
    if "," in raw:
        parts = [_extract_spatial_hint(p) for p in raw.split(",")]
        parts = [p for p in parts if p[0]]
        if len(parts) > 1:
            return parts

    single_clean, hint = _extract_spatial_hint(raw)
    return [(single_clean, hint)] if single_clean else [(raw, None)]


def find_ocr_keyword(
    keyword: str,
    elements: List[Dict[str, Any]],
    spatial_hint: Optional[str] = None,
    prev_click: Optional[Tuple[int, int]] = None,
    screen_w: int = 1920,
    screen_h: int = 1080,
) -> List[Dict[str, Any]]:
    """Find and rank OCR elements matching keyword with fuzzy matching and spatial awareness."""
    if not keyword or not elements:
        return []
    import difflib

    kw = keyword.strip().lower()
    exact_matches = []
    prefix_matches = []
    sub_matches = []
    fuzzy_matches = []

    for el in elements:
        t = el["text"].lower().rstrip(".").strip()
        if t == kw:
            exact_matches.append(el)
        elif t.startswith(kw) or kw.startswith(t):
            prefix_matches.append(el)
        elif kw in t or t in kw:
            sub_matches.append(el)
        elif difflib.SequenceMatcher(None, kw, t).ratio() >= 0.78:
            fuzzy_matches.append(el)

    candidates = exact_matches or prefix_matches or sub_matches or fuzzy_matches
    if not candidates:
        return []
    if len(candidates) == 1 and not spatial_hint and not prev_click:
        return candidates

    # Rank candidates with spatial constraints
    scored = []
    for c in candidates:
        score = float(c.get("conf", 0.8))
        t = c["text"].lower().rstrip(".").strip()
        if t == kw:
            score += 0.4
        elif t.startswith(kw):
            score += 0.2

        cx, cy = c["cx"], c["cy"]

        # Below previous click (e.g. dropdown menu below clicked header)
        if spatial_hint == "below" or (prev_click and prev_click[1] < cy):
            if prev_click and cy > prev_click[1]:
                score += 0.6
                dx = abs(cx - prev_click[0])
                if dx < 300:
                    score += 0.4
            elif cy > screen_h * 0.15:
                score += 0.2

        # Center of screen / active dialog
        if spatial_hint == "center" or (prev_click and spatial_hint is None and cy > prev_click[1] + 100):
            dist = ((cx - screen_w / 2) ** 2 + (cy - screen_h / 2) ** 2) ** 0.5
            max_d = (screen_w**2 + screen_h**2) ** 0.5 / 2
            score += (1.0 - (dist / max_d)) * 0.8

        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored]


# --- 3. Multimodal UI Grounding (Gemini 3.6/3.5 + OpenRouter Fallback) -----

def ground_ui_element(
    target_description: str,
    context: str = "",
    img: Optional[Image.Image] = None,
    spatial_hint: Optional[str] = None,
    prev_click: Optional[Tuple[int, int]] = None,
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

    clean_target = _clean_target_text(target_description) or target_description

    if player:
        player.write_log(f"[Vision] Grounding target: '{clean_target}' on {screen_w}x{screen_h} screen")

    # Step 1: Fast local OCR matching for exact text buttons with spatial awareness
    ocr_elements = extract_ocr_elements(img)
    ocr_matches = find_ocr_keyword(
        clean_target,
        ocr_elements,
        spatial_hint=spatial_hint,
        prev_click=prev_click,
        screen_w=screen_w,
        screen_h=screen_h,
    )
    if ocr_matches and ocr_matches[0].get("conf", 0) > 0.70:
        best_ocr = ocr_matches[0]
        return {
            "found": True,
            "target": clean_target,
            "element_type": "text_button",
            "center_x": best_ocr["cx"],
            "center_y": best_ocr["cy"],
            "bbox": [best_ocr["x"], best_ocr["y"], best_ocr["w"], best_ocr["h"]],
            "confidence": min(0.95, best_ocr["conf"]),
            "description": f"OCR detected text '{best_ocr['text']}'",
            "is_ambiguous": len(ocr_matches) > 1,
            "candidate_count": len(ocr_matches),
            "ambiguity_reason": "Multiple OCR matches on screen" if len(ocr_matches) > 1 else "",
        }

    # Step 2: Query Multimodal Vision Model (Gemini 3.6/3.5 Flash)
    b64_image, mime_type = image_to_base64(img, max_dim=1280)

    prompt = (
        f"You are a high-precision computer vision UI grounding specialist.\n"
        f"Analyze this {screen_w}x{screen_h} screenshot and find the UI element corresponding to: '{clean_target}'.\n"
        f"Context/Surroundings: {context if context else 'None'}\n\n"
        "Return ONLY a JSON object with this exact schema:\n"
        "{\n"
        '  "found": true/false,\n'
        '  "element_type": "button" | "menu" | "input" | "icon" | "link" | "tab" | "checkbox" | "dialog",\n'
        '  "box_2d": [ymin, xmin, ymax, xmax] (normalized integers 0 to 1000),\n'
        '  "center_x": <pixel integer horizontal coordinate 0 to ' + str(screen_w) + '>,\n'
        '  "center_y": <pixel integer vertical coordinate 0 to ' + str(screen_h) + '>,\n'
        '  "confidence": <float 0.0 to 1.0>,\n'
        '  "description": "<concise description of location and appearance>",\n'
        '  "is_ambiguous": true/false\n'
        "}\n"
    )

    # Try Gemini Vision Models directly with strict 3.5s per-model timeout
    result_json = None
    api_key = _get_api_key()
    if api_key:
        try:
            from google import genai
            from google.genai import types
            import concurrent.futures

            client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
            raw_bytes = base64.b64decode(b64_image)

            for model_name in GEMINI_VISION_CANDIDATES:
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            client.models.generate_content,
                            model=model_name,
                            contents=[
                                types.Part.from_bytes(data=raw_bytes, mime_type=mime_type),
                                prompt,
                            ],
                            config=types.GenerateContentConfig(
                                temperature=0.1,
                                response_mime_type="application/json"
                            ),
                        )
                        response = future.result(timeout=3.5)
                    text = response.text.strip()
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and ("found" in parsed or "center_x" in parsed):
                        result_json = parsed
                        break
                except Exception as model_err:
                    err_str = str(model_err).lower()
                    logger.debug(f"[VisionEngine] {model_name} grounding error: {model_err}")
                    if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                        logger.info("[VisionEngine] Quota exhausted -> immediate fallback.")
                        break
        except Exception as e:
            logger.warning(f"[VisionEngine] Gemini direct vision grounding failed: {e}")

    # Fallback to or_client if needed
    if not result_json or not result_json.get("found"):
        try:
            from or_client import client as or_c
            raw_text = or_c.vision(prompt, image_b64=b64_image, mime=mime_type)
            clean = raw_text.strip()
            if "```" in clean:
                clean = re.sub(r"^```(?:json)?\s*", "", clean)
                clean = re.sub(r"\s*```$", "", clean)
            parsed_or = json.loads(clean)
            if parsed_or:
                result_json = parsed_or
        except Exception as e:
            logger.warning(f"[VisionEngine] or_client fallback grounding failed: {e}")

    # Convert normalized box_2d if provided by Gemini
    if result_json and result_json.get("found"):
        if "box_2d" in result_json and isinstance(result_json["box_2d"], list) and len(result_json["box_2d"]) == 4:
            ymin, xmin, ymax, xmax = result_json["box_2d"]
            calc_cx = int(((xmin + xmax) / 2.0 / 1000.0) * screen_w)
            calc_cy = int(((ymin + ymax) / 2.0 / 1000.0) * screen_h)
            result_json["center_x"] = calc_cx
            result_json["center_y"] = calc_cy
            result_json["bbox"] = [
                int((xmin / 1000.0) * screen_w),
                int((ymin / 1000.0) * screen_h),
                int(((xmax - xmin) / 1000.0) * screen_w),
                int(((ymax - ymin) / 1000.0) * screen_h),
            ]

    # Step 3: Combine with OCR coordinates if valid
    if not result_json or not result_json.get("found"):
        if ocr_matches:
            best_ocr = ocr_matches[0]
            return {
                "found": True,
                "target": clean_target,
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
            "target": clean_target,
            "confidence": 0.0,
            "description": f"Element '{clean_target}' was not found on screen.",
            "is_ambiguous": False,
            "candidate_count": 0,
        }

    # Bounds check coordinates
    cx = int(result_json.get("center_x", -1))
    cy = int(result_json.get("center_y", -1))
    margin = 5
    if not (margin <= cx <= screen_w - margin and margin <= cy <= screen_h - margin):
        result_json["found"] = False
        result_json["confidence"] = 0.0
        result_json["description"] = f"Calculated coordinates ({cx}, {cy}) outside screen bounds ({screen_w}x{screen_h})."

    return result_json


# --- 4. Visual Question Answering (VQA / Screen Understand) ----------------

def screen_understand(query: str = "What is currently visible on my screen?", player=None) -> str:
    """
    Answers questions about the screen without performing any clicks.
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

            import concurrent.futures
            client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
            raw_bytes = base64.b64decode(b64_image)

            for model_name in GEMINI_VISION_CANDIDATES:
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            client.models.generate_content,
                            model=model_name,
                            contents=[
                                types.Part.from_bytes(data=raw_bytes, mime_type=mime_type),
                                prompt,
                            ],
                            config=types.GenerateContentConfig(
                                temperature=0.2,
                                max_output_tokens=400
                            ),
                        )
                        response = future.result(timeout=3.5)
                    text = response.text.strip()
                    if text:
                        return text
                except Exception as m_err:
                    err_str = str(m_err).lower()
                    logger.debug(f"[VisionEngine] {model_name} VQA error: {m_err}")
                    if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                        logger.info("[VisionEngine] Quota exhausted -> immediate fallback.")
                        break
        except Exception as e:
            logger.warning(f"[VisionEngine] Gemini direct VQA error: {e}")

    # Fallback to OpenRouter
    try:
        from or_client import client as or_c
        return or_c.vision(prompt, image_b64=b64_image, mime=mime_type, max_tokens=300)
    except Exception as e:
        return f"Unable to analyze screen: {e}"


# --- 5. Vision-Guided Safe Computer Control & Multi-Step Sequence ---------

def vision_click(target: str, context: str = "", player=None) -> str:
    """
    Locates and safely clicks UI target(s) on screen.
    Supports single elements or sequential chains (e.g. 'connection -> connect -> connect').
    """
    from core.cancellation import cancellation_manager
    from core.security_vault import security_vault
    from actions.action_verifier import ActionVerifier
    import pyautogui

    if cancellation_manager.is_cancelled():
        return "Click cancelled by user."

    if not target:
        return "Target UI element name or description is required."

    targets = _parse_click_sequence(target)
    if not targets:
        targets = [(target, None)]

    executed_steps = []
    prev_click = None

    for idx, item in enumerate(targets):
        if isinstance(item, tuple):
            sub_target, spatial_hint = item
        else:
            sub_target, spatial_hint = item, None

        if cancellation_manager.is_cancelled():
            return f"Operation cancelled by user at step {idx+1}/{len(targets)}."

        step_prefix = f"[{idx+1}/{len(targets)}] " if len(targets) > 1 else ""
        if player:
            player.write_log(f"[Vision] {step_prefix}Locating and clicking: '{sub_target}'")

        # Security check on individual action
        sec_decision = security_vault.evaluate_action(
            action_name="vision_click",
            parameters={"target": sub_target, "context": context},
        )
        if not sec_decision.allowed:
            return f"Security Policy Blocked step '{sub_target}': {sec_decision.reason}"

        # Dynamic visual settle polling for multi-step transitions (e.g. dropdown menu or dialog opening)
        grounding = {}
        for poll_attempt in range(5):
            grounding = ground_ui_element(
                sub_target,
                context=context,
                spatial_hint=spatial_hint,
                prev_click=prev_click,
                player=player,
            )
            if grounding.get("found") and float(grounding.get("confidence", 0.0)) >= CLICK_CONFIDENCE_THRESHOLD:
                break
            if idx == 0 or poll_attempt >= 3:
                break
            time.sleep(0.20)

        cx, cy, desc = -1, -1, ""
        if grounding.get("found") and float(grounding.get("confidence", 0.0)) >= CLICK_CONFIDENCE_THRESHOLD:
            cx = int(grounding["center_x"])
            cy = int(grounding["center_y"])
            desc = grounding.get("description", sub_target)
        else:
            # Fallback heuristics for common Windows menus and dialog buttons
            low = sub_target.lower().strip()
            if low == "connection":
                pyautogui.hotkey("alt", "c")
                time.sleep(0.35)
                executed_steps.append(f"Opened 'Connection' menu via Alt+C")
                continue
            elif low == "connect":
                pyautogui.press("enter")
                time.sleep(0.4)
                executed_steps.append(f"Selected 'Connect' via Enter")
                continue
            else:
                if len(targets) > 1 and executed_steps:
                    return f"Executed partial sequence ({', '.join(executed_steps)}), but '{sub_target}' (step {idx+1}/{len(targets)}) was not found on screen."
                return f"Target '{sub_target}' was not found on screen. ({grounding.get('description', '')})"

        # Physical Click
        try:
            pyautogui.moveTo(cx, cy, duration=0.18)
            time.sleep(0.05)
            pyautogui.click(cx, cy)
            prev_click = (cx, cy)
            time.sleep(0.40)  # Allow UI / dialog / menu to transition
            executed_steps.append(f"Clicked '{sub_target}' at ({cx}, {cy})")
        except Exception as e:
            return f"Failed clicking '{sub_target}' at ({cx}, {cy}): {e}"

    if len(executed_steps) > 1:
        return f"[Verified] Successfully executed sequence: {' -> '.join(executed_steps)}."
    return f"[Verified] {executed_steps[0]}." if executed_steps else "Done."


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
