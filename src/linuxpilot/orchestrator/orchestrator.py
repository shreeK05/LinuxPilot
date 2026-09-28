"""
Task Orchestrator
Main orchestration engine that coordinates all components.
Implements the full FSM lifecycle: plan → policy → execute → verify → checkpoint → review.
"""

import time
import threading
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import logging

from linuxpilot.models import (
    Plan, Step, ExecutionContext, VerificationResult,
    ActionExecutionResult, Risk,
)
from linuxpilot.orchestrator.fsm import OrchestratorFSM, StateTransition, OrchestratorState
from linuxpilot.planning.planner import Planner
from linuxpilot.planning.policy import PolicyEngine
from linuxpilot.llm.gateway import LLMGateway
from linuxpilot.workspace.overlay import OverlayManager
from linuxpilot.workspace.checkpoint import CheckpointManager
from linuxpilot.workspace.commit import CommitManager
from linuxpilot.workspace.diff import DiffAnalyzer
from linuxpilot.audit.chain import AuditChain
from linuxpilot.sandbox.manager import SandboxManager
from linuxpilot.verify.postconditions import PostconditionVerifier
from linuxpilot.verify.invariants import InvariantChecker
from linuxpilot.actions.ladder import ActionLadder
from linuxpilot.config import settings

logger = logging.getLogger(__name__)


class BudgetExceeded(Exception):
    """Raised when a budget is exceeded"""
    pass


class TaskOrchestrator:
    """
    Main orchestration engine.
    Coordinates planning, policy, execution, verification, and recovery.

    Implements the reliability contract:
    - No real files modified until human approves a commit
    - Every mistake detected, undone, and recorded
    - Machine-checkable postconditions and global invariants
    """

    def __init__(
        self,
        task_id: str,
        goal: str,
        context: ExecutionContext,
        llm_gateway: LLMGateway,
        planner: Planner,
        policy_engine: PolicyEngine,
        on_state_change: Optional[Callable] = None,
        on_audit_event: Optional[Callable] = None,
    ):
        self.task_id = task_id
        self.goal = goal
        self.context = context
        self.llm_gateway = llm_gateway
        self.planner = planner
        self.policy_engine = policy_engine
        self.mode = "hybrid"  # api | gui | hybrid

        self.fsm = OrchestratorFSM()
        self.on_state_change = on_state_change
        self.on_audit_event = on_audit_event

        # Managers
        self.overlay_mgr = OverlayManager()
        self.sandbox_mgr = SandboxManager()
        self.audit_chain = AuditChain(task_id)

        # Runtime state
        self.plan: Optional[Plan] = None
        self.current_step_index = 0
        self.workspace_info: Optional[Dict] = None
        self.checkpoint_mgr: Optional[CheckpointManager] = None
        self.commit_mgr: Optional[CommitManager] = None
        self.invariant_checker: Optional[InvariantChecker] = None
        self.postcondition_verifier = PostconditionVerifier()
        self.action_ladder: Optional[ActionLadder] = None

        # Budgets
        self.step_count = 0
        self.retries_per_step: Dict[str, int] = {}
        self.rollback_count = 0
        self.replan_count = 0
        self.start_time: Optional[float] = None

        # Watchdog
        self.watchdog_thread: Optional[threading.Thread] = None
        self.watchdog_cancel = threading.Event()
        self._aborted = False

    def _transition(self, to_state: OrchestratorState, reason: str = "", context_data: Dict = None):
        """Internal state transition with callback"""
        try:
            transition = self.fsm.transition_to(to_state, reason, context_data)
            if self.on_state_change:
                self.on_state_change(transition, self.context)
        except ValueError as e:
            logger.warning(f"Invalid state transition: {e}")

    def _audit(self, kind: str, payload: Dict, step: Optional[str] = None):
        """Internal audit logging with callback"""
        entry = self.audit_chain.append(kind, payload, step)
        if self.on_audit_event:
            self.on_audit_event(kind, "SUCCESS", payload, self.context)

    def start(self) -> bool:
        """
        Start the task execution.

        Returns:
            True if started successfully
        """
        try:
            self.start_time = time.time()
            self._transition(OrchestratorState.INIT, "Task started")
            self._audit("TASK_STARTED", {"goal": self.goal, "mode": self.mode})

            # Create workspace
            allowed_root = self.context.allowed_roots[0] if self.context.allowed_roots else "~/Downloads"
            self.workspace_info = self.overlay_mgr.create_task_workspace(
                self.task_id, allowed_root,
            )

            # Try to mount overlay (will fail on non-Linux, which is OK for development)
            try:
                self.overlay_mgr.mount_overlay(self.workspace_info)
            except Exception as e:
                logger.warning(f"Overlay mount failed (expected on non-Linux): {e}")
                # Continue without mount — use workspace_info paths directly

            # Initialize managers
            self.checkpoint_mgr = CheckpointManager(self.workspace_info)
            self.commit_mgr = CommitManager(self.workspace_info)
            self.invariant_checker = InvariantChecker(self.context)

            # Set real_data_path for baseline
            self.context.real_data_path = self.workspace_info.get("lower_dir")
            if self.context.real_data_path:
                self.invariant_checker.initialize_baseline()

            # Initialize action ladder
            workspace_root = self.workspace_info.get("mount_point") or self.workspace_info.get("upper_dir")
            self.action_ladder = ActionLadder(workspace_root, mode=self.mode)

            # Create sandbox (best-effort on Linux)
            try:
                self.sandbox_mgr.create_sandbox(self.task_id)
            except Exception as e:
                logger.warning(f"Sandbox creation failed (non-critical): {e}")

            # Start watchdog
            self._start_watchdog()

            # ── Planning phase ──
            self._transition(OrchestratorState.PLANNING, "Starting planning")

            plan = None
            plan_retries = 0
            max_plan_retries = 2

            while plan is None and plan_retries <= max_plan_retries:
                try:
                    plan = self.planner.create_plan(self.goal)
                except Exception as e:
                    plan_retries += 1
                    logger.warning(f"Planning attempt {plan_retries} failed: {e}")
                    if plan_retries > max_plan_retries:
                        raise RuntimeError(f"Planning failed after {max_plan_retries + 1} attempts: {e}")

            self.plan = plan
            self._audit("PLAN_CREATED", {
                "steps_count": len(self.plan.steps),
                "steps": [{"id": s.id, "tool": s.tool, "intent": s.intent} for s in self.plan.steps],
            })

            # ── Policy check phase ──
            self._transition(OrchestratorState.POLICY_CHECK, "Checking policy")
            max_risk, forbidden_steps = self._check_plan_policy()

            if forbidden_steps:
                self._audit("FORBIDDEN_STEPS_BLOCKED", {
                    "blocked": [s.id for s in forbidden_steps],
                })
                # Remove forbidden steps from plan
                self.plan.steps = [s for s in self.plan.steps if s not in forbidden_steps]
                if not self.plan.steps:
                    raise RuntimeError("All plan steps were forbidden by policy")

            if max_risk >= Risk.DESTRUCTIVE:
                self._transition(
                    OrchestratorState.WAITING_APPROVAL,
                    f"Requires approval (risk={max_risk})"
                )
                self._audit("APPROVAL_REQUIRED", {"max_risk": int(max_risk)})
                return True  # Wait for approval

            # ── Start execution ──
            self._transition(OrchestratorState.READY, "Ready to execute")
            self._execute_plan()

            return True

        except BudgetExceeded as e:
            logger.warning(f"Budget exceeded: {e}")
            self._transition(OrchestratorState.ABORTED, f"Budget exceeded: {e}")
            self._audit("TASK_ABORTED", {"reason": str(e)})
            self._cleanup()
            return False
        except Exception as e:
            logger.exception("Task failed to start")
            self._transition(OrchestratorState.FAILED, f"Start failed: {e}")
            self._audit("TASK_FAILED", {"error": str(e)})
            self._cleanup()
            return False

    def resume_with_approval(self, approved: bool) -> bool:
        """Resume after approval decision"""
        try:
            if approved:
                self._audit("APPROVAL_GRANTED", {})
                self._transition(OrchestratorState.READY, "Approved, ready to execute")
                self._execute_plan()
                return True
            else:
                self._audit("APPROVAL_REJECTED", {})
                self._transition(OrchestratorState.FAILED, "Approval rejected")
                self._cleanup()
                return False
        except Exception as e:
            logger.exception("Resume failed")
            self._transition(OrchestratorState.FAILED, f"Resume failed: {e}")
            self._cleanup()
            return False

    def _check_plan_policy(self) -> tuple[Risk, list[Step]]:
        """Check policy for all steps in plan. Returns (max_risk, forbidden_steps)"""
        max_risk = Risk.READ_ONLY
        forbidden = []
        for step in self.plan.steps:
            risk = self.policy_engine.classify(step, self.context)
            if risk == Risk.FORBIDDEN:
                forbidden.append(step)
                self._audit("violation", {
                    "step_id": step.id,
                    "tool": step.tool,
                    "risk": "FORBIDDEN",
                    "reason": "Policy engine blocked this step",
                }, step=step.id)
            max_risk = max(max_risk, risk)

        return max_risk, forbidden

    def _execute_plan(self):
        """Execute the plan step by step"""
        self._transition(OrchestratorState.EXECUTING, "Starting execution")

        while self.current_step_index < len(self.plan.steps):
            if self._aborted:
                break

            # Check budgets
            try:
                self._check_budgets()
            except BudgetExceeded as e:
                self._transition(OrchestratorState.ABORTED, str(e))
                self._audit("TASK_ABORTED", {"reason": str(e)})
                self._cleanup()
                return

            step = self.plan.steps[self.current_step_index]
            self.context.current_step_id = step.id

            success = self._execute_step(step)

            if success:
                self.current_step_index += 1
                self.step_count += 1
            else:
                # Recovery failed
                break

        if self.current_step_index >= len(self.plan.steps):
            self._transition(OrchestratorState.REVIEW, "Plan completed, waiting for review")
            self._audit("PLAN_COMPLETED", {"steps_executed": self.current_step_index})
        elif not self._aborted:
            self._transition(OrchestratorState.FAILED, "Execution failed")
            self._audit("TASK_FAILED", {"failed_at_step": self.current_step_index})

    def _execute_step(self, step: Step) -> bool:
        """Execute a single step with retry and recovery"""
        max_retries = settings.MAX_RETRIES_PER_STEP
        retries = self.retries_per_step.get(step.id, 0)

        while retries <= max_retries:
            self._audit("STEP_STARTED", {
                "step_id": step.id,
                "intent": step.intent,
                "tool": step.tool,
                "retry": retries,
            }, step=step.id)

            # ── Execute action ──
            result = self._execute_action(step)

            if result.success:
                # ── Verify postconditions ──
                self._transition(OrchestratorState.VERIFYING, f"Verifying {step.id}")

                if step.postconditions:
                    verification = self.postcondition_verifier.verify(step.postconditions)
                else:
                    # No postconditions — consider verified
                    verification = VerificationResult(success=True, details={"note": "no postconditions"})

                if verification.success:
                    # ── Check global invariants ──
                    invariant_ok, invariant_error = True, None
                    if self.invariant_checker:
                        invariant_ok, invariant_error = self.invariant_checker.check_all(self.workspace_info)

                    if invariant_ok:
                        # ── Create checkpoint ──
                        try:
                            self.checkpoint_mgr.create_checkpoint(step.id)
                        except Exception as e:
                            logger.warning(f"Checkpoint creation failed (non-critical): {e}")

                        self._audit("STEP_COMPLETED", {
                            "step_id": step.id,
                            "duration_ms": result.duration_ms,
                            "tool": step.tool,
                        }, step=step.id)
                        self._transition(OrchestratorState.EXECUTING, "Step completed")
                        return True
                    else:
                        self._audit("INVARIANT_VIOLATION", {
                            "error": invariant_error,
                            "step_id": step.id,
                        }, step=step.id)
                        return self._handle_step_failure(step, f"Invariant violation: {invariant_error}")
                else:
                    self._audit("VERIFICATION_FAILED", {
                        "error": verification.error,
                        "step_id": step.id,
                    }, step=step.id)
                    # Don't immediately fail — retry
                    retries += 1
                    self.retries_per_step[step.id] = retries
                    if retries <= max_retries:
                        self._transition(
                            OrchestratorState.RETRYING,
                            f"Verification failed for {step.id}, retrying ({retries}/{max_retries})"
                        )
                        self._transition(OrchestratorState.EXECUTING, "Retrying step")
                        continue
                    else:
                        return self._handle_step_failure(step, f"Verification failed: {verification.error}")
            else:
                self._audit("ACTION_FAILED", {
                    "error": result.error,
                    "step_id": step.id,
                }, step=step.id)

                retries += 1
                self.retries_per_step[step.id] = retries
                if retries <= max_retries:
                    self._transition(
                        OrchestratorState.RETRYING,
                        f"Action failed for {step.id}, retrying ({retries}/{max_retries})"
                    )
                    self._transition(OrchestratorState.EXECUTING, "Retrying step")
                    continue
                else:
                    return self._handle_step_failure(step, f"Action failed: {result.error}")

        return False

    def _execute_action(self, step: Step) -> ActionExecutionResult:
        """Execute a single action through the action ladder"""
        if self.action_ladder:
            return self.action_ladder.execute(step)
        else:
            # Fallback — shouldn't happen in production
            return ActionExecutionResult(
                success=False,
                error="Action ladder not initialized",
            )

    def _handle_step_failure(self, step: Step, error: str) -> bool:
        """Handle step failure with rollback and replan"""
        # Try rollback
        if self.rollback_count < settings.MAX_ROLLBACKS_PER_TASK:
            self._transition(OrchestratorState.ROLLING_BACK, f"Rolling back from {step.id}")
            self.rollback_count += 1

            if self.current_step_index > 0:
                prev_step = self.plan.steps[self.current_step_index - 1]
                try:
                    if self.checkpoint_mgr.restore_checkpoint(prev_step.id):
                        self._audit("ROLLBACK_COMPLETED", {
                            "to_step": prev_step.id,
                            "reason": error,
                        })

                        # Try replan
                        if self.replan_count < settings.MAX_REPLANS_PER_TASK:
                            return self._try_replan(step, error)
                        return False
                except Exception as e:
                    self._audit("ROLLBACK_FAILED", {"error": str(e)})

        return False

    def _try_replan(self, failed_step: Step, error: str) -> bool:
        """Attempt to create a new plan after failure"""
        self._transition(OrchestratorState.REPLANNING, f"Replanning after {failed_step.id}")
        self.replan_count += 1

        try:
            new_plan = self.planner.replan(
                self.goal,
                self.plan,
                failed_step,
                error,
                [s.id for s in self.plan.steps[:self.current_step_index]],
            )
            self.plan = new_plan
            self.current_step_index = 0
            self._audit("PLAN_REGENERATED", {
                "new_steps_count": len(new_plan.steps),
            })
            self._transition(OrchestratorState.PLANNING, "Replanned")
            self._transition(OrchestratorState.POLICY_CHECK, "Re-checking policy")
            max_risk, forbidden = self._check_plan_policy()
            self.plan.steps = [s for s in self.plan.steps if s not in forbidden]

            if not self.plan.steps:
                return False

            self._transition(OrchestratorState.READY, "Re-plan ready")
            return True  # Will restart execution in the main loop
        except Exception as e:
            self._audit("REPLAN_FAILED", {"error": str(e)})
            return False

    def _check_budgets(self):
        """Check if any budget is exceeded"""
        if self.step_count >= settings.MAX_STEPS_PER_TASK:
            raise BudgetExceeded(f"Max steps exceeded ({self.step_count}/{settings.MAX_STEPS_PER_TASK})")

        if self.start_time and (time.time() - self.start_time) > settings.MAX_WALL_CLOCK_SECONDS:
            raise BudgetExceeded(
                f"Wall clock time exceeded ({time.time() - self.start_time:.0f}s/{settings.MAX_WALL_CLOCK_SECONDS}s)"
            )

    def _start_watchdog(self):
        """Start watchdog thread for timeout enforcement"""
        def watchdog():
            while not self.watchdog_cancel.wait(timeout=10):
                if self.start_time and (time.time() - self.start_time) > settings.MAX_WALL_CLOCK_SECONDS:
                    logger.warning("Watchdog: time exceeded, aborting task")
                    self._aborted = True
                    self._cleanup()
                    break

        self.watchdog_thread = threading.Thread(target=watchdog, daemon=True, name=f"watchdog-{self.task_id}")
        self.watchdog_thread.start()

    def commit_changes(self) -> bool:
        """Commit changes from overlay to real data"""
        try:
            if not self.workspace_info:
                raise RuntimeError("No workspace to commit")

            # Analyze changes
            diff_analyzer = DiffAnalyzer(self.workspace_info)
            changes = diff_analyzer.analyze()

            from linuxpilot.workspace.commit import Change, ChangeKind
            change_objects = []
            for change in changes:
                kind_map = {
                    "add": ChangeKind.ADD,
                    "modify": ChangeKind.MODIFY,
                    "delete": ChangeKind.DELETE,
                    "replace_dir": ChangeKind.REPLACE_DIR,
                }
                change_objects.append(Change(
                    kind=kind_map.get(change["kind"], ChangeKind.ADD),
                    rel_path=change["path"],
                ))

            if not change_objects:
                self._audit("COMMIT_EMPTY", {"message": "No changes to commit"})
                self._transition(OrchestratorState.COMPLETED, "No changes to commit")
                self._cleanup()
                return True

            # Begin commit with WAL
            journal_file = self.commit_mgr.begin_commit(self.task_id, change_objects)

            # Apply changes
            for change in change_objects:
                if not self.commit_mgr.apply_change(journal_file, change):
                    # Rollback partial commit
                    self.commit_mgr.rollback_commit(journal_file)
                    raise RuntimeError(f"Failed to apply change: {change.rel_path}")

            # Finalize commit
            if not self.commit_mgr.finalize_commit(journal_file):
                raise RuntimeError("Failed to finalize commit")

            self._audit("COMMIT_COMPLETED", {"changes_count": len(change_objects)})
            self._transition(OrchestratorState.COMPLETED, "Changes committed")
            self._cleanup()
            return True

        except Exception as e:
            logger.exception("Commit failed")
            self._audit("COMMIT_FAILED", {"error": str(e)})
            return False

    def discard_changes(self) -> bool:
        """Discard all changes — real data untouched"""
        try:
            self._audit("DISCARD", {})

            if self.workspace_info:
                self.overlay_mgr.discard_task(self.workspace_info)

            self._cleanup()
            return True

        except Exception as e:
            logger.exception("Discard failed")
            return False

    def _cleanup(self):
        """Cleanup resources"""
        # Stop watchdog
        if self.watchdog_thread:
            self.watchdog_cancel.set()

        # Destroy sandbox
        try:
            self.sandbox_mgr.destroy_sandbox(self.task_id)
        except Exception:
            pass

        # Unmount overlay
        if self.workspace_info and self.workspace_info.get("mounted"):
            try:
                self.overlay_mgr.unmount_overlay(self.workspace_info)
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        """Get current task status"""
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "state": self.fsm.current_state.value,
            "mode": self.mode,
            "current_step": self.current_step_index,
            "total_steps": len(self.plan.steps) if self.plan else 0,
            "step_count": self.step_count,
            "rollback_count": self.rollback_count,
            "replan_count": self.replan_count,
            "elapsed_time": time.time() - self.start_time if self.start_time else 0,
            "budgets": {
                "max_steps": settings.MAX_STEPS_PER_TASK,
                "max_wall_clock": settings.MAX_WALL_CLOCK_SECONDS,
                "max_rollbacks": settings.MAX_ROLLBACKS_PER_TASK,
            },
        }
