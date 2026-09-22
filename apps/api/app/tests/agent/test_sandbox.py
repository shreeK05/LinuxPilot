import pytest
import platform
from app.agent.sandbox.manager import SandboxManager
from app.agent.sandbox.exceptions import UnsupportedPlatformError
from app.agent.models import ActionDefinition, SandboxConfig
from app.agent.actions.registry import ActionExecutionResult
from app.agent.executor import ExecutionEngine
from app.agent.policy import PolicyEngine, RiskLevel

def test_sandbox_unsupported_platform_guard():
    # If on windows, running in sandbox should gracefully return success=False and error="UNSUPPORTED_PLATFORM..."
    manager = SandboxManager()
    
    action = ActionDefinition(
        action_type="test",
        parameters={},
        sandbox_config=SandboxConfig(required=True, cpu_limit_shares=1024, memory_limit_mb=512)
    )
    
    def mock_handler():
        return ActionExecutionResult(success=True, output="should not run on windows")
        
    result = manager.execute_in_sandbox(action, mock_handler)
    
    is_windows = platform.system().lower() == "windows"
    
    if is_windows:
        assert result.success is False
        assert "UNSUPPORTED_PLATFORM" in result.error
    else:
        # On Linux it should run (since it's a stub right now, but would test actual sandbox in production)
        assert result.success is True
        assert result.output == "should not run on windows"

def test_policy_engine_sandbox_requirement():
    policy = PolicyEngine()
    
    # Action without sandbox, high risk
    action1 = ActionDefinition(
        action_type="filesystem.delete", 
        parameters={}, 
        risk_level=RiskLevel.LEVEL_4_DESTRUCTIVE,
        sandbox_config=SandboxConfig(required=False)
    )
    
    decision1 = policy.evaluate(action1)
    # Should block because Sandbox is required for >= LEVEL 3
    assert decision1.decision.value == "BLOCK"
    assert "MUST be configured to run in a sandbox" in decision1.reason
    
    # Action with sandbox, high risk
    action2 = ActionDefinition(
        action_type="filesystem.delete", 
        parameters={}, 
        risk_level=RiskLevel.LEVEL_4_DESTRUCTIVE,
        sandbox_config=SandboxConfig(required=True, cpu_limit_shares=100)
    )
    
    decision2 = policy.evaluate(action2)
    # Should require snapshot (and approval conceptually, but returns the highest block which is SNAPSHOT)
    assert decision2.decision.value == "REQUIRE_SNAPSHOT"
    assert "requires a system snapshot and sandbox" in decision2.reason

def test_execution_engine_sandbox_routing():
    # Setup mock registry
    class MockRegistry:
        def get_handler(self, action_type):
            class MockHandler:
                def execute(self, act):
                    return ActionExecutionResult(success=True, output="handler executed")
            return MockHandler()
            
    engine = ExecutionEngine(MockRegistry(), PolicyEngine())
    
    # Low risk action, no sandbox
    action1 = ActionDefinition(action_type="test", parameters={}, risk_level=RiskLevel.LEVEL_0_READ_ONLY)
    res1 = engine.execute_action(action1)
    assert res1.success is True
    assert res1.output == "handler executed"
    
    # High risk action, requires sandbox
    action2 = ActionDefinition(
        action_type="test_high", 
        parameters={}, 
        risk_level=RiskLevel.LEVEL_3_HIGH_IMPACT,
        sandbox_config=SandboxConfig(required=True, cpu_limit_shares=500, memory_limit_mb=500)
    )
    
    res2 = engine.execute_action(action2)
    
    # On Windows, ExecutionEngine will attempt to use SandboxManager, which will return UNSUPPORTED_PLATFORM
    is_windows = platform.system().lower() == "windows"
    if is_windows:
        assert res2.success is False
        assert "UNSUPPORTED_PLATFORM" in res2.error
    else:
        assert res2.success is True
        assert res2.output == "handler executed"
