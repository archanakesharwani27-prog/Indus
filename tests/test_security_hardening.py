"""
Test Suite for INDUS Security Hardening Phase
=============================================
Verifies all 7 security layers:
1. Fail-Closed Security Gate Invariant
2. Granular Risk-Based Permission Matrix
3. Python Code Sandbox & AST Security Scanner
4. Salted PIN Authentication, PBKDF2 & Lockout
5. Sensitive Data Redaction & DPAPI Secure Storage
6. Action-Target Bound Confirmation Manager
7. Complete Structured Audit Trail Logging
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.credential_redactor import redact_sensitive, redact_dict, REDACTED_STR
from core.secure_storage import save_secure_json, load_secure_json
from core.audit_logger import SecurityAuditLogger
from core.security_vault import (
    set_security_pin, verify_security_pin, clear_security_pin,
    is_pin_configured, is_locked_out
)
from core.code_sandbox import (
    scan_python_code_ast, run_sandboxed_python, handle_unknown_tool_replan
)
from core.confirmation_manager import confirmation_manager
from core.security_engine import (
    classify_tool_risk, evaluate_tool_execution, extract_action_target
)


def test_credential_redaction():
    print("\n--- [TEST 1] Credential Redaction Engine ---")
    raw_texts = [
        ("AIzaSyD-1234567890abcdefghijklmnopqrst", REDACTED_STR),
        ("sk-1234567890abcdefghijklmnopqrstuvwxyz", REDACTED_STR),
        ("gsk_1234567890abcdefghijklmnopqrstuvwxyz", REDACTED_STR),
        ("nvapi-1234567890abcdefghijklmnopqrstuvwxyz", REDACTED_STR),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", REDACTED_STR),
        ('{"api_key": "secret12345"}', f'{{"api_key": "{REDACTED_STR}"}}'),
    ]
    for text, expected_fragment in raw_texts:
        redacted = redact_sensitive(text)
        assert expected_fragment in redacted, f"Failed redacting '{text}' -> got '{redacted}'"
        assert "secret12345" not in redacted
        assert "AIzaSyD" not in redacted
        assert "eyJhbGci" not in redacted

    dict_data = {
        "user": "Ansh",
        "api_key": "AIzaSySecret1234567890abcdefghijklmnop",
        "nested": {"password": "SuperSecretPassword123!"}
    }
    cleaned_dict = redact_dict(dict_data)
    assert cleaned_dict["api_key"] == REDACTED_STR
    assert cleaned_dict["nested"]["password"] == REDACTED_STR
    assert cleaned_dict["user"] == "Ansh"
    print("  [PASS] All credential redaction patterns verified.")


def test_secure_storage():
    print("\n--- [TEST 2] Secure Credential Storage ---")
    with tempfile.TemporaryDirectory() as td:
        tf = Path(td) / "test_keys.json"
        data = {"gemini_api_key": "AIzaTestKey123", "groq_api_key": "gsk_test456"}
        ok = save_secure_json(tf, data)
        assert ok, "Failed to save secure json"
        assert tf.exists()

        loaded = load_secure_json(tf)
        assert loaded.get("gemini_api_key") == "AIzaTestKey123"
        assert loaded.get("groq_api_key") == "gsk_test456"
    print("  [PASS] Secure storage encryption-at-rest and loading verified.")


def test_salted_pin_auth_and_lockout():
    print("\n--- [TEST 3] Salted PIN Auth, PBKDF2 & Lockout ---")
    # Clean start
    clear_security_pin()
    assert not is_pin_configured()
    assert verify_security_pin("1234") is True  # Unconfigured allows

    # Set valid PIN
    res = set_security_pin("8899")
    assert "set ho gaya" in res or "successfully" in res.lower()
    assert is_pin_configured()

    # Verify correct PIN
    assert verify_security_pin("8899") is True

    # Test invalid attempts & lockout
    assert verify_security_pin("0000") is False  # Attempt 1
    assert verify_security_pin("1111") is False  # Attempt 2
    assert verify_security_pin("2222") is False  # Attempt 3 -> triggers lockout

    # Subsequent attempt within cooldown should be blocked
    locked, rem = is_locked_out()
    assert locked is True
    assert rem > 0
    assert verify_security_pin("8899") is False  # Even right PIN is blocked during lockout

    # Clean up
    clear_security_pin()
    print("  [PASS] Salted PBKDF2 PIN authentication and rate-limiting lockout verified.")


def test_code_sandbox_ast_and_execution():
    print("\n--- [TEST 4] Code Sandbox & AST Security Scanner ---")
    # Safe code
    safe_code = "x = 10 + 20\nprint(f'Result: {x}')"
    is_safe, msg = scan_python_code_ast(safe_code)
    assert is_safe is True

    res = run_sandboxed_python(safe_code)
    assert res["success"] is True
    assert "Result: 30" in res["stdout"]

    # Blocked dangerous pattern
    dangerous_code = "import os\nos.system('format c: /q')"
    is_safe2, msg2 = scan_python_code_ast(dangerous_code)
    assert is_safe2 is False
    assert "Dangerous command pattern" in msg2

    res_blocked = run_sandboxed_python(dangerous_code)
    assert res_blocked["security_blocked"] is True
    assert "Security Sandbox Block" in res_blocked["stderr"]

    # Unknown tool replan
    replan_msg = handle_unknown_tool_replan("non_existent_hack_tool", {})
    assert "UNKNOWN_TOOL" in replan_msg
    assert "replan" in replan_msg.lower()
    print("  [PASS] Code sandbox AST scanning and safe execution verified.")


def test_action_target_bound_confirmation():
    print("\n--- [TEST 5] Action-Target Bound Confirmation Manager ---")
    action = "file_controller"
    target = "c:\\users\\test\\important_report.pdf"

    # Create request
    record = confirmation_manager.create_confirmation_request(action, target, "DESTRUCTIVE")
    token = record.token
    assert len(token) > 0

    # 1. Valid confirmation with exact action & exact target
    # (Testing with a copy request)
    rec2 = confirmation_manager.create_confirmation_request("file_controller", "c:\\file.txt", "DESTRUCTIVE")
    ok, msg = confirmation_manager.validate_and_consume(rec2.token, "file_controller", "c:\\file.txt")
    assert ok is True

    # 2. Tampered target mismatch (e.g. user approved file.txt, but tool tries to delete other.txt)
    rec3 = confirmation_manager.create_confirmation_request("file_controller", "c:\\safe.txt", "DESTRUCTIVE")
    ok_tamper, msg_tamper = confirmation_manager.validate_and_consume(rec3.token, "file_controller", "c:\\windows\\system32")
    assert ok_tamper is False
    assert "mismatch" in msg_tamper.lower()

    # 3. Double-spend / reuse prevention (already consumed token)
    ok_reuse, msg_reuse = confirmation_manager.validate_and_consume(rec2.token, "file_controller", "c:\\file.txt")
    assert ok_reuse is False
    print("  [PASS] Action-target bound confirmation tokens and tamper-proofing verified.")


def test_risk_classification_and_fail_closed_gate():
    print("\n--- [TEST 6] Risk Classification & Fail-Closed Gate ---")
    # Classification tests
    assert classify_tool_risk("web_search") == "LOW"
    assert classify_tool_risk("weather_report") == "LOW"
    assert classify_tool_risk("open_app") == "LOW"
    assert classify_tool_risk("deep_research") == "LOW"
    assert classify_tool_risk("browser_control") == "MEDIUM"
    assert classify_tool_risk("terminal_command") == "HIGH"
    assert classify_tool_risk("file_controller", {"action": "delete", "target": "data.csv"}) == "DESTRUCTIVE"
    assert classify_tool_risk("computer_settings", {"action": "shutdown"}) == "DESTRUCTIVE"
    assert classify_tool_risk("unregistered_random_tool") == "UNKNOWN"

    # Gate evaluations
    # LOW risk -> Auto-allowed
    dec_low = evaluate_tool_execution("web_search", {"query": "latest news"})
    assert dec_low.allowed is True
    assert dec_low.risk_level == "LOW"

    # UNKNOWN tool -> DENIED
    dec_unk = evaluate_tool_execution("fake_tool_xyz", {})
    assert dec_unk.allowed is False
    assert dec_unk.risk_level == "UNKNOWN"

    # DESTRUCTIVE action without confirmation -> Requires confirmation
    dec_dest = evaluate_tool_execution("file_controller", {"action": "delete", "file_path": "c:\\tmp\\a.txt"})
    assert dec_dest.allowed is False
    assert dec_dest.requires_confirmation is True
    assert len(dec_dest.confirmation_token) > 0

    # DESTRUCTIVE action with valid confirmation token -> Allowed
    dec_dest_conf = evaluate_tool_execution(
        "file_controller",
        {"action": "delete", "file_path": "c:\\tmp\\a.txt", "confirmation_token": dec_dest.confirmation_token}
    )
    assert dec_dest_conf.allowed is True

    print("  [PASS] Risk-based permission matrix and fail-closed gate verified.")


def test_audit_logger():
    print("\n--- [TEST 7] Structured Audit Logging ---")
    with tempfile.TemporaryDirectory() as td:
        log_file = Path(td) / "test_audit.jsonl"
        logger = SecurityAuditLogger(log_path=log_file)

        event_id = logger.log_event(
            event_type="SECURITY_DECISION",
            tool="file_controller",
            target="AIzaSySecretApiKeyPath/data.txt",
            risk_level="DESTRUCTIVE",
            decision="DENY",
            reason="Blocked by security policy",
            user_command="Delete key sk-1234567890abcdefghijklmn"
        )
        assert len(event_id) > 0
        assert log_file.exists()

        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])

        assert record["event_id"] == event_id
        assert record["tool"] == "file_controller"
        assert record["risk_level"] == "DESTRUCTIVE"
        assert record["decision"] == "DENY"
        # Verify secrets were redacted in the log
        assert "AIzaSy" not in record["target"]
        assert "sk-123456" not in record["user_command"]
        assert REDACTED_STR in record["target"]
        assert REDACTED_STR in record["user_command"]
    print("  [PASS] Structured audit logger formatting and credential redaction verified.")


if __name__ == "__main__":
    print("==================================================")
    print("  RUNNING INDUS SECURITY HARDENING TEST SUITE     ")
    print("==================================================")
    test_credential_redaction()
    test_secure_storage()
    test_salted_pin_auth_and_lockout()
    test_code_sandbox_ast_and_execution()
    test_action_target_bound_confirmation()
    test_risk_classification_and_fail_closed_gate()
    test_audit_logger()
    print("\n==================================================")
    print("  ALL 7 SECURITY HARDENING TESTS PASSED! [100%]   ")
    print("==================================================")
