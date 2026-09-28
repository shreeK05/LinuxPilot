import pytest
import os
from app.agent.sandbox.subprocess_runner import SafeSubprocessRunner
from app.agent.actions.terminal_handlers import TerminalSafeHandler
from app.agent.models import ActionDefinition

import sys

def test_safe_subprocess_allowed_command():
    runner = SafeSubprocessRunner()
    runner.ALLOWED_COMMANDS.add(sys.executable)
    result = runner.run([sys.executable, "-c", "print('hello')"])
    assert result.success is True
    assert "hello" in result.output["stdout"]

def test_safe_subprocess_disallowed_command():
    runner = SafeSubprocessRunner()
    result = runner.run(["bash", "-c", "echo hello"])
    assert result.success is False
    assert "not in the allowlist" in result.error

def test_safe_subprocess_env_sanitization():
    os.environ["API_KEY_TEST"] = "secret123"
    os.environ["DATABASE_URL"] = "postgres://..."
    runner = SafeSubprocessRunner()
    env = runner._sanitize_env()
    assert "API_KEY_TEST" not in env
    assert "DATABASE_URL" not in env
    # Clean up
    del os.environ["API_KEY_TEST"]
    del os.environ["DATABASE_URL"]

def test_terminal_safe_handler_string_command():
    handler = TerminalSafeHandler()
    runner = SafeSubprocessRunner()
    runner.ALLOWED_COMMANDS.add(sys.executable)
    # We must patch the handler's execution to use our modified allowlist, or we just temporarily add to the class
    SafeSubprocessRunner.ALLOWED_COMMANDS.add(sys.executable)
    SafeSubprocessRunner.ALLOWED_COMMANDS.add(sys.executable.replace(chr(92), '/'))
    
    action = ActionDefinition(
        action_type="terminal.safe",
        parameters={"command": f"\"{sys.executable.replace(chr(92), '/')}\" -c \"print('test string')\""},
        timeout_seconds=5
    )
    result = handler.execute(action)
    assert result.success is True
    assert "test string" in result.output["stdout"]

def test_terminal_safe_handler_list_command():
    handler = TerminalSafeHandler()
    action = ActionDefinition(
        action_type="terminal.safe",
        parameters={"command": [sys.executable, "-c", "print('test list')"]},
        timeout_seconds=5
    )
    result = handler.execute(action)
    assert result.success is True
    assert "test list" in result.output["stdout"]

def test_safe_subprocess_output_limit():
    runner = SafeSubprocessRunner()
    SafeSubprocessRunner.ALLOWED_COMMANDS.add(sys.executable)
    result = runner.run([sys.executable, "-c", "print('x' * 2000)"], max_output_bytes=5)
    assert result.success is False
    assert "Output exceeded maximum size" in result.error
