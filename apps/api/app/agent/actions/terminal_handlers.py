from typing import List, Dict, Any
import shlex
from app.agent.models import ActionDefinition
from app.agent.actions.registry import ActionHandler, ActionExecutionResult
from app.agent.sandbox.subprocess_runner import SafeSubprocessRunner

class TerminalSafeHandler(ActionHandler):
    """
    Handler for the terminal.safe action.
    Executes a command using the SafeSubprocessRunner.
    """
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        command = action.parameters.get("command")
        
        if not command:
            return ActionExecutionResult(success=False, output=None, error="Missing 'command' parameter")
            
        # Parse command string into a list if it's a string
        if isinstance(command, str):
            try:
                command_list = shlex.split(command)
            except ValueError as e:
                return ActionExecutionResult(success=False, output=None, error=f"Failed to parse command string: {str(e)}")
        elif isinstance(command, list):
            command_list = [str(arg) for arg in command]
        else:
            return ActionExecutionResult(success=False, output=None, error="'command' must be a string or list of strings")

        if not command_list:
            return ActionExecutionResult(success=False, output=None, error="Command is empty")
            
        runner = SafeSubprocessRunner()
        timeout = action.timeout_seconds
        return runner.run(command_list, timeout_seconds=timeout)
