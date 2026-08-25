# actions/git_controller.py
# INDUS Autonomous Git & Terminal Engineering Suite
# Voice and command control for Git operations and CLI terminal commands

import os
import sys
import subprocess
import shutil
from pathlib import Path


def _get_default_repo_path(repo_path: str = "") -> str:
    """Resolve repository path with fallback to workspace root or current directory."""
    if repo_path and os.path.exists(repo_path):
        return repo_path
    base = Path(__file__).resolve().parent.parent
    if (base / ".git").exists():
        return str(base)
    # Check parent directory
    if (base.parent / ".git").exists():
        return str(base.parent)
    return str(base)


def git_action(action: str, repo_path: str = "", message: str = "") -> str:
    """
    Executes voice-controllable Git actions:
    - status: Summarizes current branch and modified/staged/untracked files.
    - commit_and_push: Runs `git add .`, `git commit -m "<msg>"`, and `git push`.
    - pull: Runs `git pull`.
    - log: Summarizes the last 3 commits.
    - branch: Shows current and available branches.
    """
    action = (action or "status").lower().strip().replace(" ", "_").replace("-", "_")
    target_dir = _get_default_repo_path(repo_path)

    if not shutil.which("git"):
        return "Git is not installed or not in system PATH."

    try:
        if action in ("status", "git_status", "check"):
            res = subprocess.run(
                ["git", "status", "-s", "-b"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=15
            )
            if res.returncode != 0:
                return f"Git status error: {res.stderr.strip()}"

            output = res.stdout.strip()
            if not output:
                return "Working tree is clean. No uncommitted changes."

            lines = output.splitlines()
            branch_info = lines[0] if lines else ""
            changes = lines[1:] if len(lines) > 1 else []
            change_summary = f"{len(changes)} modified file(s)" if changes else "clean tree"
            return f"Git Status on {branch_info}: {change_summary}.\n" + "\n".join(lines[:10])

        elif action in ("commit_and_push", "push", "save", "commit"):
            commit_msg = (message or "").strip()
            if not commit_msg:
                commit_msg = "Update codebase via INDUS AI Assistant"

            # 1. git add .
            add_res = subprocess.run(["git", "add", "."], cwd=target_dir, capture_output=True, text=True, timeout=20)
            if add_res.returncode != 0:
                return f"Git add failed: {add_res.stderr.strip()}"

            # 2. git commit -m
            commit_res = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=20
            )

            # 3. git push
            push_res = subprocess.run(
                ["git", "push"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=45
            )
            if push_res.returncode == 0:
                return f"Changes committed and pushed successfully with message: '{commit_msg}'."
            else:
                return f"Committed: '{commit_msg}', but push encountered: {push_res.stderr.strip() or push_res.stdout.strip()}"

        elif action in ("pull", "git_pull", "update", "sync"):
            pull_res = subprocess.run(
                ["git", "pull"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=35
            )
            if pull_res.returncode == 0:
                out = pull_res.stdout.strip()
                return f"Git pull complete: {out[:120]}"
            return f"Git pull failed: {pull_res.stderr.strip()}"

        elif action in ("log", "git_log", "history", "recent"):
            log_res = subprocess.run(
                ["git", "log", "-n", "3", "--pretty=format:%h - %an, %ar : %s"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=15
            )
            if log_res.returncode == 0:
                return f"Recent Commits:\n{log_res.stdout.strip()}"
            return f"Git log failed: {log_res.stderr.strip()}"

        elif action in ("branch", "branches"):
            branch_res = subprocess.run(
                ["git", "branch", "-a"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if branch_res.returncode == 0:
                return f"Git Branches:\n{branch_res.stdout.strip()}"
            return f"Git branch failed: {branch_res.stderr.strip()}"

        return f"Unknown Git action: '{action}'. Available: status, commit_and_push, pull, log, branch."

    except subprocess.TimeoutExpired:
        return f"Git action '{action}' timed out."
    except Exception as e:
        return f"Git operation error: {e}"


def terminal_command(command: str, cwd: str = "", timeout: int = 30) -> str:
    """
    Safely executes arbitrary developer CLI commands (e.g. npm run dev, pytest, flutter build).
    Returns standard output and error stream summaries.
    """
    cmd = (command or "").strip()
    if not cmd:
        return "No terminal command provided to execute."

    exec_dir = cwd if cwd and os.path.exists(cwd) else _get_default_repo_path()

    # Block destructive root formats if accidental
    blocked = [
        "format c:", "rmdir /s /q c:\\windows", "del /f /s /q c:\\windows",
        "rm -rf /", "mkfs", ":(){ :|:& };:", "dd if=/dev/zero"
    ]
    if any(b in cmd.lower() for b in blocked):
        from core.audit_logger import audit_logger
        audit_logger.log_event(
            event_type="SECURITY_ALERT",
            tool="terminal_command",
            target=cmd,
            risk_level="DESTRUCTIVE",
            decision="DENY",
            reason="Blocked hazardous terminal command pattern",
            execution_status="BLOCKED"
        )
        return f"Execution blocked: Command '{cmd}' contains hazardous system destructive patterns."

    try:
        from core.credential_redactor import redact_sensitive
        from core.audit_logger import audit_logger

        res = subprocess.run(
            cmd,
            cwd=exec_dir,
            shell=True,
            capture_output=True,
            text=True,
            timeout=max(5, min(120, int(timeout or 30)))
        )

        stdout = redact_sensitive((res.stdout or "").strip())
        stderr = redact_sensitive((res.stderr or "").strip())

        audit_logger.log_event(
            event_type="TOOL_INVOCATION",
            tool="terminal_command",
            target=cmd,
            risk_level="HIGH",
            decision="ALLOW",
            reason="Terminal command executed",
            execution_status="SUCCESS" if res.returncode == 0 else "FAILURE"
        )

        if res.returncode == 0:
            out_preview = stdout if len(stdout) < 600 else stdout[:600] + "\n...[truncated]"
            return f"Command succeeded (exit 0):\n{out_preview or 'No output.'}"
        else:
            err_preview = stderr if len(stderr) < 600 else stderr[:600] + "\n...[truncated]"
            return f"Command failed (exit {res.returncode}):\n{err_preview or stdout or 'Unknown error'}"

    except subprocess.TimeoutExpired:
        return f"Terminal command '{cmd}' timed out after {timeout} seconds."
    except Exception as e:
        return f"Terminal execution error: {e}"


def git_controller(parameters: dict = None, player=None) -> str:
    """Main tool dispatch entry point for git_controller."""
    from core.cancellation import cancellation_manager
    params = parameters or {}
    action = params.get("action", "status")
    repo_path = params.get("repo_path", "")
    message = params.get("message", "")

    if cancellation_manager.is_cancelled():
        return "Git operation cancelled by user."

    if not shutil.which("git"):
        return "[ENVIRONMENT_UNAVAILABLE] Git is not installed or not in system PATH."

    if player:
        player.write_log(f"[Git] {action} {message[:30] if message else ''}")

    return git_action(action=action, repo_path=repo_path, message=message)
