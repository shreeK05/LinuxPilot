import pytest
import time
from app.agent.executor import ExecutionEngine
from app.agent.models import ActionDefinition
from app.agent.actions.registry import ActionRegistry, ActionExecutionResult
from app.agent.policy import PolicyEngine, PolicyDecision, PolicyDecisionResult

class MockActionHandler:
    def __init__(self, sleep_time: float):
        self.sleep_time = sleep_time
        self.action_type = "mock.action"
        
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        time.sleep(self.sleep_time)
        return ActionExecutionResult(success=True, output={"status": "done"})

class MockActionRegistry(ActionRegistry):
    def __init__(self, sleep_time: float):
        super().__init__()
        self.handler = MockActionHandler(sleep_time)
        
    def get_handler(self, action_type: str):
        return self.handler

class MockPolicyEngine(PolicyEngine):
    def evaluate(self, action: ActionDefinition) -> PolicyDecision:
        return PolicyDecision(
            decision=PolicyDecisionResult.ALLOW,
            risk_level=1,
            reason="Mock policy allow"
        )

def test_fast_action_completes_successfully():
    engine = ExecutionEngine(MockActionRegistry(sleep_time=0.1), MockPolicyEngine())
    action = ActionDefinition(
        action_type="mock.action",
        parameters={},
        timeout_seconds=2
    )
    result = engine.execute_action(action)
    assert result.success is True
    assert result.output == {"status": "done"}

def test_action_completing_just_before_timeout_succeeds():
    engine = ExecutionEngine(MockActionRegistry(sleep_time=0.8), MockPolicyEngine())
    action = ActionDefinition(
        action_type="mock.action",
        parameters={},
        timeout_seconds=1
    )
    result = engine.execute_action(action)
    assert result.success is True
    assert result.output == {"status": "done"}

def test_slow_action_exceeds_timeout_returns_controlled_failure():
    engine = ExecutionEngine(MockActionRegistry(sleep_time=1.5), MockPolicyEngine())
    action = ActionDefinition(
        action_type="mock.action",
        parameters={},
        timeout_seconds=1
    )
    start = time.time()
    result = engine.execute_action(action)
    duration = time.time() - start
    
    # Should timeout in ~1 second
    assert 0.9 <= duration <= 1.3
    assert result.success is False
    assert "ACTION_TIMEOUT: Action exceeded 1s limit" in result.error
