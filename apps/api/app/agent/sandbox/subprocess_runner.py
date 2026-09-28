import subprocess
import os
import shlex
from typing import List, Dict, Any, Tuple
from app.agent.actions.registry import ActionExecutionResult

class SafeSubprocessRunner:
    """
    Executes specific whitelisted commands safely without shell=True.
    Sanitizes environment variables.
    """
    
    # Whitelisted base commands.
    ALLOWED_COMMANDS = {
        "ls", "cat", "echo", "grep", "uname", "df", "free", "find",
        "mkdir", "cp", "mv", "rm", "head", "tail", "wc", "stat", "pwd", "tree",
        "whoami", "ps", "uptime", "date", "lsb_release", "ping", "tar", "systemctl", "top", "lscpu", "python3"
    }

    # Banned environment variables (API keys, secrets, DB urls)
    BANNED_ENV_PREFIXES = ("API_KEY", "SECRET", "PASSWORD", "TOKEN", "DATABASE", "LLM_", "AWS_", "GCP_", "AZURE_")

    def __init__(self, working_dir: str = None):
        self.working_dir = working_dir or os.getcwd()

    def _sanitize_env(self) -> Dict[str, str]:
        """Creates a clean environment for the subprocess."""
        clean_env = {}
        # Allow basic safe environment variables
        safe_keys = {"PATH", "LANG", "HOME", "USER"}
        for k, v in os.environ.items():
            if k in safe_keys:
                clean_env[k] = v
                continue
            
            # Block sensitive vars
            if any(k.upper().startswith(prefix) for prefix in self.BANNED_ENV_PREFIXES):
                continue
            
            if "KEY" in k.upper() or "SECRET" in k.upper() or "TOKEN" in k.upper():
                continue
                
            clean_env[k] = v
        
        return clean_env

    def run(self, command: List[str], timeout_seconds: int = 10, max_output_bytes: int = 1024 * 1024) -> ActionExecutionResult:
        if not command:
            return ActionExecutionResult(success=False, output=None, error="Empty command provided")

        base_cmd = command[0]
        
        if base_cmd not in self.ALLOWED_COMMANDS:
            return ActionExecutionResult(
                success=False, 
                output=None, 
                error=f"Command '{base_cmd}' is not in the allowlist. Allowed: {', '.join(sorted(self.ALLOWED_COMMANDS))}"
            )
            
        try:
            env = self._sanitize_env()
            
            import platform
            from app.agent.sandbox.resource_limits import preexec_fn_limits
            is_windows = platform.system() == "Windows"
            
            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "cwd": self.working_dir,
                "env": env,
                "text": True,
                "shell": False
            }
            if not is_windows:
                kwargs["preexec_fn"] = preexec_fn_limits
            
            process = subprocess.Popen(command, **kwargs)
            
            try:
                stdout, stderr = process.communicate(timeout=timeout_seconds)
                
                # Check output size limits
                if len(stdout.encode('utf-8')) > max_output_bytes or len(stderr.encode('utf-8')) > max_output_bytes:
                    return ActionExecutionResult(
                        success=False, 
                        output=None, 
                        error=f"Output exceeded maximum size of {max_output_bytes} bytes"
                    )
                
                output = {
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": process.returncode
                }
                return ActionExecutionResult(success=(process.returncode == 0), output=output)
                
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                return ActionExecutionResult(success=False, output=None, error=f"Command timed out after {timeout_seconds} seconds")
                
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=f"Execution error: {str(e)}")
