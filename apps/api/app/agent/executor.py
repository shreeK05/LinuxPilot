from typing import Optional, Dict, Any
from app.agent.models import ActionDefinition
from app.agent.actions.registry import ActionRegistry, ActionExecutionResult
from app.agent.policy import PolicyEngine, PolicyDecisionResult
import time

class ExecutionEngine:
    """
    Executes actions by validating policies and looking up handlers in the ActionRegistry.
    """
    def __init__(self, registry: ActionRegistry, policy_engine: PolicyEngine):
        self.registry = registry
        self.policy_engine = policy_engine

    def execute_action(self, action: ActionDefinition) -> ActionExecutionResult:
        # 1. Policy check (redundant if orchestrator does it, but good for defense-in-depth)
        decision = self.policy_engine.evaluate(action)
        if decision.decision in [PolicyDecisionResult.BLOCK, PolicyDecisionResult.REQUIRE_APPROVAL, PolicyDecisionResult.REQUIRE_SNAPSHOT]:
            # In a real system, the orchestrator handles APPROVAL and SNAPSHOT before execution. 
            # If they reached here and are BLOCKED, fail immediately.
            if decision.decision == PolicyDecisionResult.BLOCK:
                return ActionExecutionResult(
                    success=False,
                    output=None,
                    error=f"Execution blocked by policy: {decision.reason}"
                )

        # 2. Look up handler
        try:
            handler = self.registry.get_handler(action.action_type)
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=str(e))

        # 3. Execute
        # In a real engine, we'd run this asynchronously with a timeout.
        # For Phase 2, we execute synchronously.
        start_time = time.time()
        try:
            result = handler.execute(action)
            # Timeout check (simulated)
            if time.time() - start_time > action.timeout_seconds:
                return ActionExecutionResult(success=False, output=None, error="Action timed out")
            return result
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=f"Execution exception: {str(e)}")
