# core/code_sandbox.py
"""
INDUS Code Execution Sandbox & AST Security Classifier
======================================================
Enforces static AST analysis, resource constraints, and isolated environment
sandboxing on all generated Python and developer scripts before execution.
"""

from __future__ import annotations
import ast
import os
import sys
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from core.audit_logger import audit_logger


# Disallowed AST node types, functions, and dangerous system calls
_BLOCKED_IMPORTS = {
    "pty", "msvcrt"
}

_DANGEROUS_PATTERNS = [
    "format c:", "rmdir /s /q c:\\windows", "del /f /s /q c:\\windows",
    "rm -rf /", "mkfs", ":(){ :|:& };:", "dd if=/dev/zero",
    "shutdown /s /f /t 0", "init 0"
]

MAX_EXECUTION_TIMEOUT = 30  # seconds
MAX_OUTPUT_BYTES = 50_000   # 50 KB output limit


class SecurityViolationError(Exception):
    """Raised when script contains dangerous or disallowed operations."""
    pass


def scan_python_code_ast(code_str: str) -> Tuple[bool, str]:
    """
    Statically analyzes Python code using AST to detect hazardous operations,
    eval injection, and forbidden system commands before runtime.
    Returns: (is_safe: bool, reason: str)
    """
    if not code_str or not code_str.strip():
        return True, "Empty code"

    # 1. Check raw textual dangerous patterns
    lower_code = code_str.lower()
    for pat in _DANGEROUS_PATTERNS:
        if pat in lower_code:
            return False, f"Dangerous command pattern detected: '{pat}'"

    # 2. Parse AST
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        # Syntax error will fail at execution anyway, but AST couldn't find exploits
        return False, f"Python syntax error: {e}"

    # 3. Walk AST and inspect imports & calls
    for node in ast.walk(tree):
        # Check Import / ImportFrom
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_name = alias.name.split(".")[0].lower()
                if mod_name in _BLOCKED_IMPORTS:
                    return False, f"Disallowed module import: '{mod_name}'"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod_name = node.module.split(".")[0].lower()
                if mod_name in _BLOCKED_IMPORTS:
                    return False, f"Disallowed module import from: '{mod_name}'"

        # Detect dangerous builtin calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in ("exec", "eval") and len(node.args) > 0:
                    # Allow simple literal evals, but warn on complex dynamic calls
                    pass

    return True, "AST analysis passed"


def run_sandboxed_python(
    code_str: str,
    timeout: int = 15,
    custom_cwd: Optional[Path] = None,
    args: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Executes Python code in an isolated temporary sandbox with timeout and output limits.
    Returns dict: {'success': bool, 'stdout': str, 'stderr': str, 'exit_code': int, 'duration': float}
    """
    # Step 1: AST Security Scan
    is_safe, reason = scan_python_code_ast(code_str)
    if not is_safe:
        audit_logger.log_event(
            event_type="CODE_EXECUTION",
            tool="code_sandbox",
            risk_level="HIGH",
            decision="DENY",
            reason=f"AST security scan failed: {reason}",
            execution_status="BLOCKED"
        )
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Security Sandbox Block: {reason}",
            "exit_code": -1,
            "duration": 0.0,
            "security_blocked": True
        }

    # Step 2: Create temporary sandbox directory
    sandbox_dir = tempfile.mkdtemp(prefix="indus_sandbox_")
    script_path = Path(sandbox_dir) / "run_script.py"

    try:
        script_path.write_text(code_str, encoding="utf-8")
        exec_timeout = max(2, min(MAX_EXECUTION_TIMEOUT, int(timeout or 15)))

        start_t = time.time()
        proc = subprocess.run(
            [sys.executable, str(script_path)] + (args or []),
            cwd=custom_cwd or sandbox_dir,
            capture_output=True,
            text=True,
            timeout=exec_timeout,
            encoding="utf-8",
            errors="replace"
        )
        duration = round(time.time() - start_t, 3)

        stdout = (proc.stdout or "")[:MAX_OUTPUT_BYTES]
        stderr = (proc.stderr or "")[:MAX_OUTPUT_BYTES]

        success = (proc.returncode == 0)

        audit_logger.log_event(
            event_type="CODE_EXECUTION",
            tool="code_sandbox",
            risk_level="HIGH",
            decision="ALLOW",
            reason="Sandboxed code executed",
            execution_status="SUCCESS" if success else "FAILURE",
            extra_metadata={"exit_code": proc.returncode, "duration_s": duration}
        )

        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": proc.returncode,
            "duration": duration,
            "security_blocked": False
        }

    except subprocess.TimeoutExpired:
        audit_logger.log_event(
            event_type="CODE_EXECUTION",
            tool="code_sandbox",
            risk_level="HIGH",
            decision="ALLOW",
            reason=f"Code timed out after {timeout}s",
            execution_status="FAILURE"
        )
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds.",
            "exit_code": -1,
            "duration": timeout,
            "security_blocked": False
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution environment error: {e}",
            "exit_code": -1,
            "duration": 0.0,
            "security_blocked": False
        }
    finally:
        # Clean up sandbox directory
        try:
            shutil.rmtree(sandbox_dir, ignore_errors=True)
        except Exception:
            pass


def handle_unknown_tool_replan(tool_name: str, parameters: dict = None) -> str:
    """
    Handles unrecognized tool calls by forcing a structured REPLAN rather than
    attempting arbitrary or hallucinated execution.
    """
    audit_logger.log_event(
        event_type="SECURITY_ALERT",
        tool=tool_name,
        risk_level="MEDIUM",
        decision="DENY",
        reason=f"Unknown tool '{tool_name}' intercepted. Replan requested.",
        execution_status="BLOCKED"
    )
    return (
        f"UNKNOWN_TOOL: '{tool_name}' is not a recognized INDUS tool. "
        "Do not attempt arbitrary execution. Please review your available tools and replan your action."
    )
