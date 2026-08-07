"""
ShellExecutor - Safe command execution (PowerShell, CMD)
"""

import subprocess
import shlex
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    stdout: str
    stderr: str
    returncode: int
    command: str
    shell: str


class ShellExecutor:
    """Execute shell commands safely with allowlist/blocklist."""
    
    def __init__(
        self,
        allowed_commands: Optional[List[str]] = None,
        blocked_commands: Optional[List[str]] = None,
        require_confirmation: bool = True,
        timeout: int = 60,
    ):
        self.allowed_commands = allowed_commands or []
        self.blocked_commands = blocked_commands or [
            "format", "del /f", "rm -rf",
            "shutdown", "restart", "taskkill /f",
            "diskpart", "reg delete", "reg add",
            "bcdedit", "diskmgmt", "cipher /w",
        ]
        self.require_confirmation = require_confirmation
        self.timeout = timeout
        self._audit_log: List[Dict[str, Any]] = []
    
    def is_allowed(self, command: str) -> bool:
        """Check if command is allowed."""
        cmd_lower = command.lower().strip()
        
        # Check blocked first
        for blocked in self.blocked_commands:
            if blocked.lower() in cmd_lower:
                return False
        
        # If allowlist is configured, check it
        if self.allowed_commands:
            for allowed in self.allowed_commands:
                if allowed.lower() in cmd_lower:
                    return True
            return False
        
        return True
    
    def execute(
        self,
        command: str,
        shell: str = "powershell",
        wait: bool = True,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> CommandResult:
        """Execute a command."""
        # Check if allowed
        if not self.is_allowed(command):
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Command blocked by security policy: {command}",
                returncode=-1,
                command=command,
                shell=shell,
            )
        
        # Build command
        if shell == "powershell":
            cmd = ["powershell", "-Command", command]
        elif shell == "cmd":
            cmd = ["cmd", "/c", command]
        else:
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Unknown shell: {shell}",
                returncode=-1,
                command=command,
                shell=shell,
            )
        
        # Prepare environment
        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)
        
        try:
            if wait:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=cwd,
                    env=exec_env,
                )
                
                output = CommandResult(
                    success=result.returncode == 0,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    returncode=result.returncode,
                    command=command,
                    shell=shell,
                )
            else:
                proc = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    env=exec_env,
                )
                output = CommandResult(
                    success=True,
                    stdout=f"Process started with PID {proc.pid}",
                    stderr="",
                    returncode=0,
                    command=command,
                    shell=shell,
                )
            
            # Log to audit
            self._audit_log.append({
                "command": command,
                "shell": shell,
                "success": output.success,
                "returncode": output.returncode,
            })
            
            return output
            
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Command timed out ({self.timeout}s)",
                returncode=-1,
                command=command,
                shell=shell,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                returncode=-1,
                command=command,
                shell=shell,
            )
    
    def execute_powershell(self, command: str, **kwargs) -> CommandResult:
        """Execute PowerShell command."""
        return self.execute(command, shell="powershell", **kwargs)
    
    def execute_cmd(self, command: str, **kwargs) -> CommandResult:
        """Execute CMD command."""
        return self.execute(command, shell="cmd", **kwargs)
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get audit log."""
        return self._audit_log.copy()
    
    def clear_audit_log(self) -> None:
        """Clear audit log."""
        self._audit_log.clear()


# Global instance
_shell_executor = ShellExecutor()


def get_shell_executor() -> ShellExecutor:
    return _shell_executor