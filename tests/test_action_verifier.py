import sys
import unittest
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from actions.action_verifier import ActionVerifier, VerificationResult, DESTRUCTIVE_ACTIONS
from actions.open_app import open_app
from actions.computer_settings import computer_settings


class TestActionVerifier(unittest.TestCase):

    def setUp(self):
        self.verifier = ActionVerifier(max_retries=1)

    # 1. Verified Success Test
    def test_verified_success(self):
        # Explorer is always running on Windows
        res = self.verifier.verify_app_launch("explorer", wait_seconds=0)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.confidence, 1.0)
        self.assertFalse(res.retry_allowed)
        self.assertIn("running", res.evidence)

    # 2. Verified Failure Test
    def test_verified_failure(self):
        res = self.verifier.verify_app_launch("non_existent_fake_app_99999", wait_seconds=0)
        self.assertEqual(res.status, "FAILURE")
        self.assertGreaterEqual(res.confidence, 0.8)
        self.assertTrue(res.retry_allowed)
        self.assertIn("No process", res.evidence)

    # 3. Uncertain Result Test
    def test_uncertain_result(self):
        # When screenshots are None, visual change verification must report UNCERTAIN
        res = self.verifier.verify_visual_change(None, None, "click")
        self.assertEqual(res.status, "UNCERTAIN")
        self.assertLess(res.confidence, 0.6)
        self.assertFalse(res.retry_allowed)

    # 4. Safe Retry & Visual Change Test
    def test_visual_change_difference(self):
        img1 = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img2 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        res = self.verifier.verify_visual_change(img1, img2, "button click")
        self.assertEqual(res.status, "SUCCESS")
        self.assertGreaterEqual(res.confidence, 0.8)
        self.assertFalse(res.retry_allowed)

        # Same image -> FAILURE (no UI change) -> retry allowed
        res_same = self.verifier.verify_visual_change(img1, img1, "button click")
        self.assertEqual(res_same.status, "FAILURE")
        self.assertTrue(res_same.retry_allowed)

    # 5. Retry Limit Test
    def test_retry_limit(self):
        self.assertEqual(self.verifier.max_retries, 1)

    # 6. Destructive Actions Protection Test
    def test_destructive_actions_never_retried(self):
        for act in ["restart", "shutdown", "delete", "format", "kill", "drop", "truncate", "panic"]:
            self.assertTrue(self.verifier.is_destructive(act), f"{act} should be detected as destructive")

        # Non-destructive action
        self.assertFalse(self.verifier.is_destructive("open_app"))
        self.assertFalse(self.verifier.is_destructive("click"))
        self.assertFalse(self.verifier.is_destructive("volume_set"))

    # 7. Real Safe E2E Integration Test (Reversible Action)
    def test_real_safe_e2e_open_app(self):
        # Step A: Launch a non-existent app -> should fail closed-loop verification
        res_fail = open_app({"app_name": "fake_test_binary_xyz_123"})
        self.assertIn("verified that it is not running", res_fail)

        # Step B: System settings query test
        res_vol = computer_settings({"action": "set_volume", "value": "30"})
        self.assertIn("Volume set to 30%", res_vol)


if __name__ == "__main__":
    unittest.main()
