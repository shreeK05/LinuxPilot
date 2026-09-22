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

class ActionRegistry:
    def __init__(self):
        self._handlers: Dict[str, ActionHandler] = {}
        
        # Register test handlers
        self.register("filesystem.mock", MockFileActionHandler())
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
