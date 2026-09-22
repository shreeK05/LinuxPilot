from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from app.agent.models import ActionDefinition

class ActionExecutionResult:
    def __init__(self, success: bool, output: Any, error: str = None):
        self.success = success
        self.output = output
        self.error = error

class ActionHandler(ABC):
    """
    Abstract interface for executing an action.
    """
    @abstractmethod
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        pass

class MockFileActionHandler(ActionHandler):
    """
    Deterministic test handler for filesystem actions.
    """
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        # Mock deterministic execution
        target = action.parameters.get("target", "unknown")
        if target == "fail":
            return ActionExecutionResult(success=False, output=None, error="Mocked failure")
        return ActionExecutionResult(success=True, output=f"Mock successfully processed {target}")

class TestActionHandler(ActionHandler):
    """
    Deterministic test handler for generic testing actions.
    """
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        return ActionExecutionResult(success=True, output="Test action executed successfully")

class UnknownActionError(Exception):
    pass

from app.agent.actions.filesystem_handlers import (
    FSListDirectoryHandler, FSStatHandler, FSReadFileHandler,
    FSCreateDirectoryHandler, FSCopyHandler, FSMoveHandler,
    FSRenameHandler, FSWriteFileHandler, FSDeleteHandler
)
from app.adapters.linux.terminal.safe_commands import SafeTerminalCommands

class SystemInfoHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            target = action.parameters.get("command")
            if target == "disk_usage":
                res = SafeTerminalCommands.get_disk_usage()
            elif target == "memory_usage":
                res = SafeTerminalCommands.get_memory_usage()
            elif target == "cpu_info":
                res = SafeTerminalCommands.get_cpu_info()
            else:
                raise UnknownActionError(f"Unknown system command: {target}")
            return ActionExecutionResult(success=True, output=res)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))

class ActionRegistry:
    def __init__(self):
        self._handlers: Dict[str, ActionHandler] = {}
        
        # Filesystem
        self.register("filesystem.list_directory", FSListDirectoryHandler())
        self.register("filesystem.stat", FSStatHandler())
        self.register("filesystem.read_file", FSReadFileHandler())
        self.register("filesystem.create_directory", FSCreateDirectoryHandler())
        self.register("filesystem.copy", FSCopyHandler())
        self.register("filesystem.move", FSMoveHandler())
        self.register("filesystem.rename", FSRenameHandler())
        self.register("filesystem.write_file", FSWriteFileHandler())
        self.register("filesystem.delete", FSDeleteHandler())
        
        # System
        self.register("system.info", SystemInfoHandler())
        
        # Legacy for old tests
        self.register("test.init", TestActionHandler())
        self.register("test.search", TestActionHandler())
        self.register("test.validate", TestActionHandler())
        self.register("test.finalize", TestActionHandler())

    def register(self, action_type: str, handler: ActionHandler):
        self._handlers[action_type] = handler

    def get_handler(self, action_type: str) -> ActionHandler:
        handler = self._handlers.get(action_type)
        if not handler:
            raise UnknownActionError(f"Action type '{action_type}' is not registered.")
        return handler

# Global registry instance for Phase 2
action_registry = ActionRegistry()
