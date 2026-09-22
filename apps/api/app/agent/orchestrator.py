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
            self.goal = self.interpreter.interpret(raw_goal)
            self._audit("GOAL_UNDERSTOOD", "SUCCESS", self.goal.model_dump())
            
            # 2. PLANNING
            self._transition(AgentState.PLANNING, "Creating execution plan")
            self.plan = self.planner.create_plan(self.goal)
            self.context.plan_id = self.plan.plan_id
            self._audit("PLAN_CREATED", "SUCCESS", {"plan_id": self.plan.plan_id, "steps_count": len(self.plan.steps)})
            
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
                # In Phase 3, we pause here. The caller will persist the state and wait for API interaction.
                return

            # 4. EXECUTION LOOP
            self._transition(AgentState.READY, "Ready for execution")
            self._execute_plan()
            
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
                self._transition(AgentState.READY, "Approval granted")
                self._execute_plan()
            else:
                self._audit("APPROVAL_REJECTED", "FAILED", {"reason": reason})
                self._transition(AgentState.FAILED, f"Task rejected by user: {reason}")
        except Exception as e:
            logger.exception("Agent resume failed")
            if not self.state_machine.is_terminal():
                self._transition(AgentState.FAILED, f"Unexpected error during resume: {str(e)}")
            self._audit("TASK_FAILED", "FAILED", {"error": str(e)})

    def _execute_plan(self):
        self._transition(AgentState.EXECUTING, "Starting plan execution")
        
        while self.current_step_index < len(self.plan.steps):
            step = self.plan.steps[self.current_step_index]
            self.context.current_step_id = step.step_id
            
            # Execute step
            success = self._execute_step_with_recovery(step)
            
            if not success:
                # Recovery failed or max retries exceeded
                if not self.state_machine.is_terminal():
                    self._transition(AgentState.FAILED, f"Failed at step {step.step_id}")
                self._audit("TASK_FAILED", "FAILED", {"failed_step": step.step_id})
                return
                
            self.current_step_index += 1
            
        self._transition(AgentState.COMPLETED, "All steps completed successfully")
        self._audit("TASK_COMPLETED", "SUCCESS", {"plan_id": self.plan.plan_id})

    def _execute_step_with_recovery(self, step: PlanStep) -> bool:
        self._audit("ACTION_STARTED", "IN_PROGRESS", {"step_id": step.step_id, "action_type": step.action.action_type})
        
        while True:
            # 1. Execute Action
            result = self.execution_engine.execute_action(step.action)
            
            if result.success:
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
                    recovery_decision = self._handle_recovery(step, verification.error, verification)
            else:
                self._audit("ACTION_FAILED", "FAILED", {"step_id": step.step_id, "error": result.error})
                recovery_decision = self._handle_recovery(step, result.error)
                
            # Process recovery decision
            if recovery_decision.decision == RecoveryDecisionResult.RETRY:
                self._transition(AgentState.RETRYING, f"Retrying step {step.step_id}: {recovery_decision.reason}")
                # Loop continues to retry
            elif recovery_decision.decision == RecoveryDecisionResult.REPLAN:
                self._transition(AgentState.REPLANNING, "Replanning required")
                # Not fully implemented in Phase 2, so treat as failure
                return False
            else:
                # FAIL, ROLLBACK, ASK_USER -> Abort step
                return False

    def _handle_recovery(self, step: PlanStep, error: str, verification_result=None) -> RecoveryDecisionResult:
        self._transition(AgentState.RETRYING if "retry" in error.lower() else AgentState.FAILED, "Evaluating recovery")
        
        retries = self.action_retries.get(step.step_id, 0)
        decision = self.recovery_engine.determine_recovery(step.action, error, retries, verification_result)
        
        self._audit("RECOVERY_STARTED", "IN_PROGRESS", decision.model_dump())
        
        if decision.decision == RecoveryDecisionResult.RETRY:
            self.action_retries[step.step_id] = retries + 1
            
        return decision
