from typing import Optional, List, Callable, Any, Dict
from app.agent.models import (
    AgentState, GoalUnderstanding, ExecutionPlan, PlanStep, 
    ActionDefinition, PolicyDecisionResult, RecoveryDecisionResult
)
from app.agent.state_machine import AgentStateMachine, StateTransition
from app.agent.goal_understanding import GoalInterpreter
from app.agent.planner import Planner
from app.agent.policy import PolicyEngine
from app.agent.executor import ExecutionEngine
from app.agent.verifier import Verifier
from app.agent.recovery import RecoveryEngine
from app.agent.context import ExecutionContext
import logging

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Central orchestrator coordinating the agent lifecycle.
    Independent of FastAPI and Web frameworks.
    """
    def __init__(
        self,
        context: ExecutionContext,
        interpreter: GoalInterpreter,
        planner: Planner,
        policy_engine: PolicyEngine,
        execution_engine: ExecutionEngine,
        verifier: Verifier,
        recovery_engine: RecoveryEngine,
        state_machine: Optional[AgentStateMachine] = None,
        on_state_change: Optional[Callable[[StateTransition, ExecutionContext], None]] = None,
        on_audit_event: Optional[Callable[[str, str, Dict[str, Any], ExecutionContext], None]] = None
    ):
        self.context = context
        self.interpreter = interpreter
        self.planner = planner
        self.policy_engine = policy_engine
        self.execution_engine = execution_engine
        self.verifier = verifier
        self.recovery_engine = recovery_engine
        self.state_machine = state_machine or AgentStateMachine()
        self.on_state_change = on_state_change
        self.on_audit_event = on_audit_event
        
        self.goal: Optional[GoalUnderstanding] = None
        self.plan: Optional[ExecutionPlan] = None
        
        # State tracking for execution
        self.current_step_index = 0
        self.action_retries: Dict[str, int] = {}
        self.replan_count = 0
        self.max_replans = 2
        self.step_outputs: Dict[str, Any] = {}

    def _transition(self, to_state: AgentState, reason: str = None, context_data: dict = None):
        transition = self.state_machine.transition_to(to_state, reason, context_data)
        if self.on_state_change:
            self.on_state_change(transition, self.context)
        return transition

    def _audit(self, event_type: str, status: str, metadata: Dict[str, Any]):
        if self.on_audit_event:
            self.on_audit_event(event_type, status, metadata, self.context)

    def run_lifecycle(self, raw_goal: str):
        """
        Runs the full deterministic lifecycle synchronously.
        """
        try:
            self._audit("TASK_STARTED", "SUCCESS", {"raw_goal": raw_goal})
            
            # 1. UNDERSTANDING
            self._transition(AgentState.UNDERSTANDING, "Starting goal interpretation")
            
            # Bounded retry for LLM calls
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.goal = self.interpreter.interpret(raw_goal)
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"Goal interpretation failed, retrying (attempt {attempt+1}): {e}")
            
            self._audit("GOAL_UNDERSTOOD", "SUCCESS", self.goal.model_dump())
            
            # 2. PLANNING
            self._transition(AgentState.PLANNING, "Creating execution plan")
            
            for attempt in range(max_retries):
                try:
                    self.plan = self.planner.create_plan(self.goal)
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"Plan creation failed, retrying (attempt {attempt+1}): {e}")
            
            self.context.plan_id = self.plan.plan_id
            self.context.plan_id = self.plan.plan_id
            self._audit("PLAN_CREATED", "SUCCESS", {"plan_id": self.plan.plan_id, "steps_count": len(self.plan.steps)})
            
            self._run_policy_and_execute_loop()
            
        except Exception as e:
            logger.exception("Agent lifecycle failed")
            if not self.state_machine.is_terminal():
                self._transition(AgentState.FAILED, f"Unexpected error: {str(e)}")
            self._audit("TASK_FAILED", "FAILED", {"error": str(e)})

    def resume_from_approval(self, approved: bool, reason: str = ""):
        """
        Resumes the orchestrator after a human approval decision.
        Must be called when current_state == WAITING_APPROVAL.
        """
        try:
            if approved:
                self._audit("APPROVAL_GRANTED", "SUCCESS", {"reason": reason})
                self._run_policy_and_execute_loop(skip_policy_check=True)
            else:
                self._audit("APPROVAL_REJECTED", "FAILED", {"reason": reason})
                self._transition(AgentState.FAILED, f"Task rejected by user: {reason}")
        except Exception as e:
            logger.exception("Agent resume failed")
            if not self.state_machine.is_terminal():
                self._transition(AgentState.FAILED, f"Unexpected error during resume: {str(e)}")
            self._audit("TASK_FAILED", "FAILED", {"error": str(e)})

    def _run_policy_and_execute_loop(self, skip_policy_check: bool = False):
        while True:
            if not skip_policy_check:
                # 3. POLICY CHECK
                self._transition(AgentState.POLICY_CHECK, "Evaluating plan against policy")
                
                max_risk_decision = None
                for step in self.plan.steps:
                    decision = self.policy_engine.evaluate(step.action)
                    if not max_risk_decision or decision.risk_level > max_risk_decision.risk_level:
                        max_risk_decision = decision
                        
                if max_risk_decision and max_risk_decision.decision == PolicyDecisionResult.BLOCK:
                    self._audit("POLICY_CHECKED", "FAILED", max_risk_decision.model_dump())
                    self._transition(AgentState.FAILED, f"Plan blocked by policy: {max_risk_decision.reason}")
                    return
                    
                self._audit("POLICY_CHECKED", "SUCCESS", max_risk_decision.model_dump() if max_risk_decision else {})
                
                if max_risk_decision and max_risk_decision.decision in [PolicyDecisionResult.REQUIRE_APPROVAL, PolicyDecisionResult.REQUIRE_SNAPSHOT]:
                    self._transition(AgentState.WAITING_APPROVAL, f"Waiting for approval: {max_risk_decision.reason}", max_risk_decision.model_dump())
                    return

            skip_policy_check = False # Only skip first iteration if approved

            # 4. EXECUTION LOOP
            self._transition(AgentState.READY, "Ready for execution")
            self._execute_plan()
            
            if self.state_machine.current_state == AgentState.REPLANNING:
                # Plan was regenerated, loop back to POLICY_CHECK
                continue
            break

    def _execute_plan(self):
        self._transition(AgentState.EXECUTING, "Starting plan execution")
        
        while self.current_step_index < len(self.plan.steps):
            step = self.plan.steps[self.current_step_index]
            self.context.current_step_id = step.step_id
            
            # Execute step
            success = self._execute_step_with_recovery(step)
            
            if not success:
                if self.state_machine.current_state == AgentState.REPLANNING:
                    # Replanning successful, break execution loop to go back to policy check
                    return
                    
                # Recovery failed or max retries exceeded
                if not self.state_machine.is_terminal():
                    self._transition(AgentState.FAILED, f"Failed at step {step.step_id}")
                self._audit("TASK_FAILED", "FAILED", {"failed_step": step.step_id})
                return
                
            self.current_step_index += 1
            
        self._transition(AgentState.COMPLETED, "All steps completed successfully")
        self._audit("TASK_COMPLETED", "SUCCESS", {"plan_id": self.plan.plan_id})

    def _interpolate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Safely resolves {{step_id.output.key}} references using completed step outputs."""
        import re
        import copy
        
        result = copy.deepcopy(parameters)
        pattern = re.compile(r"\{\{([^}]+)\}\}")
        
        def resolve_value(val: Any) -> Any:
            if isinstance(val, str):
                matches = pattern.findall(val)
                if not matches:
                    return val
                    
                # If the entire string is a single variable, preserve type (e.g. dict/list)
                if len(matches) == 1 and val.strip() == f"{{{{{matches[0]}}}}}":
                    return self._resolve_path(matches[0])
                    
                # Otherwise string replacement
                new_str = val
                for match in matches:
                    resolved = self._resolve_path(match)
                    new_str = new_str.replace(f"{{{{{match}}}}}", str(resolved))
                return new_str
            elif isinstance(val, dict):
                return {k: resolve_value(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [resolve_value(v) for v in val]
            return val
            
        return resolve_value(result)

    def _resolve_path(self, path: str) -> Any:
        parts = path.split('.')
        if len(parts) < 2 or parts[1] != 'output':
            return f"{{{{{path}}}}}" # Unresolved
            
        step_id = parts[0]
        if step_id not in self.step_outputs:
            return f"{{{{{path}}}}}"
            
        current = self.step_outputs[step_id]
        for part in parts[2:]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                current = current[int(part)]
            else:
                return f"{{{{{path}}}}}" # Missing key
        return current

    def _execute_step_with_recovery(self, step: PlanStep) -> bool:
        self._audit("ACTION_STARTED", "IN_PROGRESS", {"step_id": step.step_id, "action_type": step.action.action_type})
        
        while True:
            # 0. Interpolate parameters safely
            try:
                interpolated_params = self._interpolate_parameters(step.action.parameters)
            except Exception as e:
                self._audit("ACTION_FAILED", "FAILED", {"step_id": step.step_id, "error": f"Parameter interpolation failed: {e}"})
                current_error = f"Interpolation error: {e}"
                recovery_decision = self._handle_recovery(step, current_error)
                if recovery_decision.decision != RecoveryDecisionResult.RETRY and recovery_decision.decision != RecoveryDecisionResult.REPLAN:
                    self._transition(AgentState.FAILED, "No safe recovery path remains")
                    return False
                continue

            import copy
            action_to_execute = copy.deepcopy(step.action)
            action_to_execute.parameters = interpolated_params
            action_to_execute.parameters["task_id"] = self.context.task_id

            # 1. Execute Action
            result = self.execution_engine.execute_action(action_to_execute)
            
            if result.success:
                self.step_outputs[step.step_id] = result.output
                self._audit("ACTION_COMPLETED", "SUCCESS", {"step_id": step.step_id, "output": result.output})
                
                # 2. Verify (if successful execution)
                self._transition(AgentState.VERIFYING, f"Verifying step {step.step_id}")
                self._audit("VERIFICATION_STARTED", "IN_PROGRESS", {"step_id": step.step_id})
                
                verification = self.verifier.verify(step.action, result.output)
                
                if verification.success:
                    self._audit("VERIFICATION_COMPLETED", "SUCCESS", verification.model_dump())
                    self._transition(AgentState.EXECUTING, "Returning to execution loop")
                    return True
                else:
                    self._audit("VERIFICATION_COMPLETED", "FAILED", verification.model_dump())
                    current_error = verification.error
                    current_verification = verification
                    recovery_decision = self._handle_recovery(step, current_error, current_verification)
            else:
                self._audit("ACTION_FAILED", "FAILED", {"step_id": step.step_id, "error": result.error})
                current_error = result.error
                current_verification = None
                recovery_decision = self._handle_recovery(step, current_error)
                
            # Process recovery decision
            if recovery_decision.decision == RecoveryDecisionResult.RETRY:
                self._transition(AgentState.RETRYING, f"Retrying step {step.step_id}: {recovery_decision.reason}")
                # Loop continues to retry
            elif recovery_decision.decision == RecoveryDecisionResult.REPLAN:
                if self.replan_count >= self.max_replans:
                    self._audit("REPLAN_FAILED", "FAILED", {"reason": "Max replans exceeded"})
                    # Fallback to ROLLBACK instead if risk is high, else FAILED
                    if step.action.risk_level >= 3 or step.action.sandbox_config.required:
                        recovery_decision = RecoveryDecisionResult.ROLLBACK # Handled below
                    else:
                        self._transition(AgentState.FAILED, "Max replans exceeded. No safe recovery path remains.")
                        return False
                else:
                    self._transition(AgentState.REPLANNING, f"Replanning. Attempt {self.replan_count + 1} of {self.max_replans}")
                    
                    try:
                        executed_steps = [s.step_id for s in self.plan.steps[:self.current_step_index]]
                        error_context = current_error if current_error else "Unknown execution error"
                        if current_verification:
                            error_context += f"\nVerification Diff:\n{current_verification.model_dump_json(indent=2)}"
                            
                        new_plan = self.planner.replan(
                            goal=self.goal,
                            current_plan=self.plan,
                            failed_step=step,
                            error=error_context,
                            executed_steps=executed_steps
                        )
                        
                        self.plan = new_plan
                        self.context.plan_id = self.plan.plan_id
                        self.replan_count += 1
                        self.current_step_index = 0
                        
                        self._audit("PLAN_REGENERATED", "SUCCESS", {
                            "replan_count": self.replan_count,
                            "new_plan_id": self.plan.plan_id,
                            "steps_count": len(self.plan.steps)
                        })
                        
                        # Trigger loop break to go back to POLICY_CHECK
                        return False
                        
                    except Exception as e:
                        self._audit("REPLAN_FAILED", "FAILED", {"error": str(e)})
                        if step.action.risk_level >= 3 or step.action.sandbox_config.required:
                            recovery_decision = RecoveryDecisionResult.ROLLBACK
                        else:
                            self._transition(AgentState.FAILED, f"Replanning failed: {e}")
                            return False
                            
            if recovery_decision == RecoveryDecisionResult.ROLLBACK or (hasattr(recovery_decision, 'decision') and recovery_decision.decision == RecoveryDecisionResult.ROLLBACK):
                self._transition(AgentState.ROLLING_BACK, "Executing task-level rollback.")
                
                # Retrieve snapshot and rollback
                from app.agent.actions.filesystem_handlers import snapshot_manager
                from app.adapters.linux.filesystem.rollback import RollbackManager
                
                task_snapshot = snapshot_manager.get_task_snapshot(self.context.task_id)
                if not task_snapshot:
                    self._audit("ROLLBACK_FAILED", "FAILED", {"error": "No task snapshot found to rollback."})
                    self._transition(AgentState.FAILED, "Rollback failed due to missing snapshot.")
                    return False
                    
                rb_manager = RollbackManager()
                try:
                    res = rb_manager.rollback_task(task_snapshot)
                    self._audit("ROLLBACK_COMPLETED", "SUCCESS", res)
                    self._transition(AgentState.FAILED, "Safely rolled back. Task execution aborted.")
                except Exception as e:
                    self._audit("ROLLBACK_FAILED", "FAILED", {"error": str(e)})
                    self._transition(AgentState.FAILED, "CRITICAL: Rollback failed. System state may be unsafe.")
                return False
            elif recovery_decision.decision != RecoveryDecisionResult.RETRY and recovery_decision.decision != RecoveryDecisionResult.REPLAN:
                # FAIL, ASK_USER -> Abort step
                self._transition(AgentState.FAILED, "No safe recovery path remains")
                return False

    def _handle_recovery(self, step: PlanStep, error: str, verification_result=None) -> RecoveryDecisionResult:
        retries = self.action_retries.get(step.step_id, 0)
        decision = self.recovery_engine.determine_recovery(step.action, error, retries, verification_result)
        
        self._audit("RECOVERY_STARTED", "IN_PROGRESS", decision.model_dump())
        
        if decision.decision == RecoveryDecisionResult.RETRY:
            self.action_retries[step.step_id] = retries + 1
            
        return decision
