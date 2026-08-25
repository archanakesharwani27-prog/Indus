import base64
import json
import sys
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from actions.vision_engine import (
    capture_screen,
    image_to_base64,
    extract_ocr_elements,
    find_ocr_keyword,
    ground_ui_element,
    screen_understand,
    vision_click,
    CLICK_CONFIDENCE_THRESHOLD,
)
from core.cancellation import cancellation_manager
from core.security_vault import security_vault


class TestVisionEngine(unittest.TestCase):

    def setUp(self):
        cancellation_manager.reset()

    def tearDown(self):
        cancellation_manager.reset()

    # Helper: Create synthetic GUI image with known buttons
    def _create_mock_gui_image(self) -> Image.Image:
        img = Image.new("RGB", (1000, 700), color=(30, 34, 42))
        draw = ImageDraw.Draw(img)

        # Draw a mock "Download" button at (800, 600) -> (950, 650)
        draw.rectangle([800, 600, 950, 650], fill=(0, 120, 215))
        draw.text((830, 615), "Download", fill=(255, 255, 255))

        # Draw a mock "Cancel" button at (100, 600) -> (250, 650)
        draw.rectangle([100, 600, 250, 650], fill=(180, 40, 40))
        draw.text((140, 615), "Cancel", fill=(255, 255, 255))

        # Draw header text
        draw.text((50, 50), "Settings and Preferences Dialog", fill=(220, 220, 220))
        return img

    # 1. Screen Capture Layer Test
    def test_screen_capture(self):
        img, w, h = capture_screen()
        self.assertIsNotNone(img)
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)

    # 2. Image to Base64 Compression Test
    def test_image_to_base64(self):
        mock_img = self._create_mock_gui_image()
        b64, mime = image_to_base64(mock_img, max_dim=800)
        self.assertEqual(mime, "image/jpeg")
        self.assertTrue(len(b64) > 100)
        # Verify decodable
        decoded = base64.b64decode(b64)
        self.assertTrue(len(decoded) > 0)

    # 3. OCR Text Extraction Test
    def test_ocr_extraction(self):
        mock_img = self._create_mock_gui_image()
        elements = extract_ocr_elements(mock_img)
        # If tesseract is installed, it will find words in mock_img
        if elements:
            found_words = [el["text"].lower() for el in elements]
            self.assertTrue(any("download" in w for w in found_words) or any("settings" in w for w in found_words))
            matches = find_ocr_keyword("Download", elements)
            if matches:
                self.assertIn("download", matches[0]["text"].lower())
                self.assertGreater(matches[0]["cx"], 0)
                self.assertGreater(matches[0]["cy"], 0)

    # 4. Structured Target Grounding with Mock Image
    def test_ground_ui_element_mock_image(self):
        mock_img = self._create_mock_gui_image()
        grounding = ground_ui_element("Download", img=mock_img)
        self.assertIn("found", grounding)
        self.assertIn("confidence", grounding)
        if grounding.get("found"):
            cx = grounding["center_x"]
            cy = grounding["center_y"]
            self.assertTrue(0 <= cx <= mock_img.width)
            self.assertTrue(0 <= cy <= mock_img.height)

    # 5. Low Confidence Rejection Guardrail
    def test_low_confidence_rejection(self):
        # Searching for non-existent target should return low confidence / not found
        mock_img = self._create_mock_gui_image()
        grounding = ground_ui_element("xyz_non_existent_unicorn_button_12345", img=mock_img)
        self.assertFalse(grounding.get("found", False))
        self.assertLess(grounding.get("confidence", 0.0), CLICK_CONFIDENCE_THRESHOLD)

    # 6. Cancellation Guardrail During Vision Processing
    def test_cancellation_during_vision(self):
        cancellation_manager.request_cancellation(reason="User voice 'STOP'")
        res = ground_ui_element("Download button")
        self.assertFalse(res.get("found", True))
        self.assertIn("cancelled", res.get("error", "").lower())

        v_res = screen_understand("What is on screen?")
        self.assertIn("cancelled", v_res.lower())

        c_res = vision_click("Download")
        self.assertIn("cancelled", c_res.lower())

    # 7. Ambiguity Handling
    def test_ambiguity_detection(self):
        # Create image with multiple "Settings" buttons
        amb_img = Image.new("RGB", (800, 600), color=(30, 30, 30))
        draw = ImageDraw.Draw(amb_img)
        draw.rectangle([50, 50, 150, 90], fill=(70, 70, 70))
        draw.text((60, 60), "Settings", fill=(255, 255, 255))
        draw.rectangle([50, 200, 150, 240], fill=(70, 70, 70))
        draw.text((60, 210), "Settings", fill=(255, 255, 255))

        elements = extract_ocr_elements(amb_img)
        matches = find_ocr_keyword("Settings", elements)
        if len(matches) > 1:
            grounding = ground_ui_element("Settings", img=amb_img)
            self.assertTrue(grounding.get("is_ambiguous", False) or grounding.get("candidate_count", 0) > 1)

    # 8. Real Safe E2E Screen Understand Test
    def test_e2e_screen_understand(self):
        answer = screen_understand("Is there any text or window visible?")
        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 5)


if __name__ == "__main__":
    unittest.main()
