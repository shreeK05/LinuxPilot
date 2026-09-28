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
        import concurrent.futures
        
        def _run_handler():
            return handler.execute(action)

        def _execute_task():
            if action.sandbox_config.required:
                from app.agent.sandbox.manager import SandboxManager
                sandbox = SandboxManager()
                return sandbox.execute_in_sandbox(action, _run_handler)
            else:
                return _run_handler()

        if action.action_type.startswith("browser."):
            # Playwright objects are strictly bound to a single thread.
            # Running them in a temporary ThreadPoolExecutor destroys the session across steps.
            # We bypass the timeout thread and run it directly on the orchestrator thread.
            try:
                return _execute_task()
            except Exception as e:
                return ActionExecutionResult(success=False, output=None, error=f"Execution exception: {str(e)}")

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_execute_task)
        try:
            return future.result(timeout=action.timeout_seconds)
        except concurrent.futures.TimeoutError:
            return ActionExecutionResult(
                success=False,
                output=None,
                error=f"ACTION_TIMEOUT: Action exceeded {action.timeout_seconds}s limit"
            )
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=f"Execution exception: {str(e)}")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
