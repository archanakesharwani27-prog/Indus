# tests/test_vision_system_phase7.py
"""
INDUS Phase 7 — Vision System Test Suite
========================================
Validates:
1. Multi-tier screen capture & base64 image compression
2. Local OCR text extraction & token bounding box calculation
3. Multimodal UI grounding cascade (Tier 0 -> Tier 3)
4. Visual action execution (vision_click, vision_type, vision_scroll, vision_drag)
5. Closed-loop ActionVerifier integration & state diff confirmation
6. Ambiguity detection and low-confidence threshold guardrails
7. Cooperative cancellation during vision operations
8. Brain / Planner multi-step visual workflow generation
9. Fail-closed security engine policy validation
"""

import base64
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.vision_manager import (
    VisionManager,
    GroundingResult,
    VisualActionResult,
    vision_manager,
    CLICK_CONFIDENCE_THRESHOLD,
)
from actions.vision_engine import (
    vision_click,
    vision_type,
    vision_scroll,
    vision_engine,
    ground_ui_element,
    screen_understand,
    capture_screen,
    extract_ocr_elements,
    image_to_base64,
)
from core.cancellation import cancellation_manager
from core.security_engine import security_engine
from agent.planner import create_agent_plan, validate_plan_schema, VALID_TOOLS


class TestVisionSystemPhase7(unittest.TestCase):

    def setUp(self):
        cancellation_manager.reset()

    def _create_mock_gui_image(self) -> Image.Image:
        """Create a synthetic desktop interface canvas for testing."""
        img = Image.new("RGB", (1000, 700), color=(30, 34, 42))
        draw = ImageDraw.Draw(img)

        # Header bar
        draw.rectangle([0, 0, 1000, 60], fill=(45, 50, 62))
        draw.text((30, 20), "INDUS Application Navigator", fill=(255, 255, 255))

        # Search Bar at (200, 120) -> (700, 170)
        draw.rectangle([200, 120, 700, 170], fill=(240, 240, 240))
        draw.text((220, 135), "Search YouTube or enter URL", fill=(80, 80, 80))

        # Primary Action Button "Download" at (750, 580) -> (920, 640)
        draw.rectangle([750, 580, 920, 640], fill=(30, 140, 240))
        draw.text((800, 600), "Download", fill=(255, 255, 255))

        # Secondary Button "Cancel" at (100, 580) -> (240, 640)
        draw.rectangle([100, 580, 240, 640], fill=(200, 50, 50))
        draw.text((145, 600), "Cancel", fill=(255, 255, 255))

        return img

    # --- 1. Screen Capture & Compression ---
    def test_01_screen_capture_and_compression(self):
        img, w, h = vision_manager.capture()
        self.assertIsNotNone(img)
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)

        b64, mime = vision_manager.compress_image(img, max_dim=800)
        self.assertEqual(mime, "image/jpeg")
        self.assertTrue(len(b64) > 50)
        decoded = base64.b64decode(b64)
        self.assertGreater(len(decoded), 0)
        print("[PASS] test_01_screen_capture_and_compression")

    # --- 2. OCR Text Extraction ---
    def test_02_ocr_text_extraction(self):
        mock_img = self._create_mock_gui_image()
        mock_data = {
            "text": ["", "Search", "YouTube", "Download", "Cancel"],
            "conf": [0, 95, 90, 99, 98],
            "left": [0, 220, 300, 800, 145],
            "top": [0, 135, 135, 600, 600],
            "width": [0, 80, 80, 80, 80],
            "height": [0, 20, 20, 20, 20],
        }
        with patch("pytesseract.image_to_data", return_value=mock_data), patch("actions.vision_engine.TESSERACT_EXE", "mock_bin"):
            # Ensure the import works
            import pytesseract
            orig_cmd = pytesseract.pytesseract.tesseract_cmd
            try:
                pytesseract.pytesseract.tesseract_cmd = "mock_bin"
                tokens = vision_manager.extract_ocr(mock_img)
                self.assertTrue(len(tokens) > 0)
                found_texts = [t["text"].lower() for t in tokens]
                self.assertTrue(any("download" in t for t in found_texts) or any("cancel" in t for t in found_texts))
                for tok in tokens:
                    self.assertIn("cx", tok)
                    self.assertIn("cy", tok)
                    self.assertTrue(0 <= tok["cx"] <= mock_img.width)
            finally:
                pytesseract.pytesseract.tesseract_cmd = orig_cmd
        print("[PASS] test_02_ocr_text_extraction")

    # --- 3. Grounding Cascade on Synthetic Canvas ---
    def test_03_grounding_synthetic_canvas(self):
        mock_img = self._create_mock_gui_image()
        # Mock Gemini response to simulate instant deterministic response
        mock_resp = {
            "found": True,
            "element_type": "button",
            "center_x": 835,
            "center_y": 610,
            "bbox": [750, 580, 170, 60],
            "confidence": 0.95,
            "description": "Blue Download Button at bottom right",
            "is_ambiguous": False,
            "candidate_count": 1,
            "ambiguity_reason": ""
        }
        with patch.object(vision_manager, "_get_gemini_key", return_value="test_key"):
            with patch("google.genai.Client") as mock_client:
                mock_gen = MagicMock()
                mock_gen.models.generate_content.return_value = MagicMock(text=json.dumps(mock_resp))
                mock_client.return_value = mock_gen

                result = vision_manager.ground("Download button", img=mock_img)
                self.assertTrue(result.found)
                self.assertEqual(result.center_x, 835)
                self.assertEqual(result.center_y, 610)
                self.assertGreaterEqual(result.confidence, 0.90)
                self.assertEqual(result.element_type, "button")
        print("[PASS] test_03_grounding_synthetic_canvas")

    # --- 4. Visual Click Execution & ActionVerifier ---
    def test_04_visual_action_click(self):
        with patch.object(vision_manager, "ground") as mock_ground:
            mock_ground.return_value = GroundingResult(
                found=True,
                target="Download button",
                center_x=835,
                center_y=610,
                confidence=0.92,
                element_type="button",
                description="Blue Download Button"
            )
            with patch("pyautogui.click") as mock_click, patch("pyautogui.moveTo") as mock_move:
                with patch("actions.action_verifier.ActionVerifier.verify_action_success") as mock_verify:
                    mock_verify.return_value = MagicMock(verified=True, details="Visual click confirmed.")
                    res = vision_manager.click("Download button")
                    self.assertTrue(res.success)
                    self.assertEqual(res.action_type, "click")
                    self.assertEqual(res.coordinates, (835, 610))
                    self.assertTrue(res.verified)
        print("[PASS] test_04_visual_action_click")

    # --- 5. Visual Type Text Execution ---
    def test_05_visual_action_type(self):
        with patch.object(vision_manager, "ground") as mock_ground:
            mock_ground.return_value = GroundingResult(
                found=True,
                target="YouTube search bar",
                center_x=450,
                center_y=145,
                confidence=0.90,
                element_type="input",
                description="Search input bar"
            )
            with patch("pyautogui.click"):
                with patch("pyautogui.hotkey"):
                    with patch("pyautogui.press"):
                        with patch("pyperclip.copy"):
                            with patch("actions.action_verifier.ActionVerifier.verify_action_success") as mock_verify:
                                mock_verify.return_value = MagicMock(verified=True, details="Text typed verified.")
                                res = vision_manager.type_text(
                                    target="YouTube search bar",
                                    text="Arijit Singh",
                                    press_enter=True,
                                    clear_first=True
                                )
                                self.assertTrue(res.success)
                                self.assertEqual(res.action_type, "type")
                                self.assertIn("Arijit Singh", res.message)
                                self.assertTrue(res.verified)
        print("[PASS] test_05_visual_action_type")

    # --- 6. Visual Scroll Execution ---
    def test_06_visual_action_scroll(self):
        with patch("pyautogui.scroll") as mock_scroll:
            with patch("actions.action_verifier.ActionVerifier.verify_action_success") as mock_verify:
                mock_verify.return_value = MagicMock(verified=True, details="Scroll verified.")
                res = vision_manager.scroll(direction="down", amount=400)
                self.assertTrue(res.success)
                self.assertEqual(res.action_type, "scroll")
                self.assertIn("400", res.message)
                mock_scroll.assert_called_with(-400)
        print("[PASS] test_06_visual_action_scroll")

    # --- 7. Ambiguity & Confidence Guardrails ---
    def test_07_ambiguity_and_low_confidence_guardrails(self):
        # 1. Low confidence test
        with patch.object(vision_manager, "ground") as mock_ground:
            mock_ground.return_value = GroundingResult(
                found=True,
                target="unclear icon",
                center_x=100,
                center_y=100,
                confidence=0.40,  # Below CLICK_CONFIDENCE_THRESHOLD (0.60)
                description="Blurry artifact"
            )
            res = vision_manager.click("unclear icon")
            self.assertFalse(res.success)
            self.assertIn("Confidence too low", res.message)

        # 2. Ambiguity test
        with patch.object(vision_manager, "ground") as mock_ground:
            mock_ground.return_value = GroundingResult(
                found=True,
                target="Settings button",
                center_x=200,
                center_y=200,
                confidence=0.85,
                is_ambiguous=True,
                candidate_count=3,
                ambiguity_reason="3 Settings icons visible on screen."
            )
            res = vision_manager.click("Settings button")
            self.assertFalse(res.success)
            self.assertIn("ambiguous", res.message.lower())
        print("[PASS] test_07_ambiguity_and_low_confidence_guardrails")

    # --- 8. Cooperative Cancellation Guardrail ---
    def test_08_cancellation_during_vision_operations(self):
        cancellation_manager.request_cancellation(reason="User voice 'STOP'")
        g_res = vision_manager.ground("Download button")
        self.assertFalse(g_res.found)
        self.assertIn("cancelled", g_res.description.lower())

        c_res = vision_manager.click("Download button")
        self.assertFalse(c_res.success)
        self.assertIn("cancelled", c_res.message.lower())

        t_res = vision_manager.type_text("Search bar", "Hello")
        self.assertFalse(t_res.success)
        self.assertIn("cancelled", t_res.message.lower())
        print("[PASS] test_08_cancellation_during_vision_operations")

    # --- 9. Planner Vision Workflow Integration ---
    def test_09_planner_vision_workflow_integration(self):
        # Verify valid tools registration in planner
        self.assertIn("vision_click", VALID_TOOLS)
        self.assertIn("vision_type", VALID_TOOLS)
        self.assertIn("vision_scroll", VALID_TOOLS)
        self.assertIn("vision_engine", VALID_TOOLS)

        # Validate multi-step vision-guided task plan parsing
        raw_plan = {
            "goal": "Chrome mein YouTube kholo aur search karo Arijit Singh",
            "steps": [
                {
                    "step_id": 1,
                    "tool": "open_app",
                    "description": "Open Google Chrome",
                    "parameters": {"app_name": "Google Chrome"},
                    "expected_result": "Chrome is active window",
                    "critical": True
                },
                {
                    "step_id": 2,
                    "tool": "vision_type",
                    "description": "Navigate to YouTube",
                    "parameters": {"target": "address bar", "text": "https://youtube.com", "press_enter": True},
                    "expected_result": "YouTube homepage loaded",
                    "critical": True
                },
                {
                    "step_id": 3,
                    "tool": "vision_type",
                    "description": "Search for artist",
                    "parameters": {"target": "YouTube search bar", "text": "Arijit Singh", "press_enter": True},
                    "expected_result": "Search results visible",
                    "critical": True
                },
                {
                    "step_id": 4,
                    "tool": "vision_click",
                    "description": "Click first song",
                    "parameters": {"target": "first video result"},
                    "expected_result": "Song starts playing",
                    "critical": True
                }
            ]
        }
        from agent.planner import validate_plan_schema
        steps = validate_plan_schema(raw_plan)
        self.assertEqual(len(steps), 4)
        self.assertEqual(steps[1].tool, "vision_type")
        self.assertEqual(steps[1].parameters["text"], "https://youtube.com")
        self.assertEqual(steps[3].tool, "vision_click")
        print("[PASS] test_09_planner_vision_workflow_integration")

    # --- 10. Security Engine Risk Policy for Vision Tools ---
    def test_10_security_engine_vision_policy(self):
        decision_click = security_engine(
            tool_name="vision_click",
            parameters={"target": "Download button"}
        )
        self.assertTrue(decision_click.allowed)
        self.assertEqual(decision_click.risk_level, "LOW")

        decision_type = security_engine(
            tool_name="vision_type",
            parameters={"target": "search bar", "text": "test query"}
        )
        self.assertTrue(decision_type.allowed)
        self.assertEqual(decision_type.risk_level, "LOW")

        decision_scroll = security_engine(
            tool_name="vision_scroll",
            parameters={"direction": "down"}
        )
        self.assertTrue(decision_scroll.allowed)
        self.assertEqual(decision_scroll.risk_level, "LOW")
        print("[PASS] test_10_security_engine_vision_policy")

    # --- 11. Unified vision_engine Dispatcher ---
    def test_11_unified_vision_engine_dispatcher(self):
        with patch("actions.vision_engine.vision_click", return_value="Clicked submit.") as mock_c:
            res_c = vision_engine({"action": "click", "target": "submit"})
            self.assertIn("submit", res_c)

        with patch("actions.vision_engine.vision_type", return_value="Typed hello.") as mock_t:
            res_t = vision_engine({"action": "type", "target": "search", "text": "hello"})
            self.assertIn("Typed hello", res_t)

        with patch("actions.vision_engine.vision_scroll", return_value="Scrolled down.") as mock_s:
            res_s = vision_engine({"action": "scroll", "direction": "down"})
            self.assertIn("Scrolled down", res_s)
        print("[PASS] test_11_unified_vision_engine_dispatcher")


if __name__ == "__main__":
    unittest.main()
