"""
Orchestrator Finite State Machine
Explicit state machine for task lifecycle
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OrchestratorState(Enum):
    """States in the orchestrator FSM"""
    INIT = "init"
    PLANNING = "planning"
    POLICY_CHECK = "policy_check"
    READY = "ready"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RETRYING = "retrying"
    REPLANNING = "replanning"
    ROLLING_BACK = "rolling_back"
    WAITING_APPROVAL = "waiting_approval"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class StateTransition:
    """Represents a state transition"""
    
    def __init__(
        self,
        from_state: OrchestratorState,
        to_state: OrchestratorState,
        reason: str,
        timestamp: str,
        context_data: Optional[Dict[str, Any]] = None,
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        self.timestamp = timestamp
        self.context_data = context_data or {}


class OrchestratorFSM:
    """
    Finite State Machine for task orchestration
    Ensures deterministic state transitions
    """
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        OrchestratorState.INIT: [
            OrchestratorState.PLANNING,
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ],
        OrchestratorState.PLANNING: [
            OrchestratorState.POLICY_CHECK,
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ],
        OrchestratorState.POLICY_CHECK: [
            OrchestratorState.READY,
            OrchestratorState.WAITING_APPROVAL,
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ],
        OrchestratorState.READY: [
            OrchestratorState.EXECUTING,
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ],
        OrchestratorState.EXECUTING: [
            OrchestratorState.VERIFYING,
            OrchestratorState.RETRYING,
            OrchestratorState.REPLANNING,
            OrchestratorState.ROLLING_BACK,
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ],
        OrchestratorState.VERIFYING: [
            OrchestratorState.EXECUTING,
            OrchestratorState.RETRYING,
            OrchestratorState.REPLANNING,
            OrchestratorState.ROLLING_BACK,
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ],
        OrchestratorState.RETRYING: [
            OrchestratorState.EXECUTING,
            OrchestratorState.REPLANNING,
            OrchestratorState.ROLLING_BACK,
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ],
        OrchestratorState.REPLANNING: [
            OrchestratorState.PLANNING,
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ],
        OrchestratorState.ROLLING_BACK: [
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ],
        OrchestratorState.WAITING_APPROVAL: [
            OrchestratorState.READY,
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ],
        OrchestratorState.REVIEW: [
            OrchestratorState.COMPLETED,
            OrchestratorState.FAILED,
        ],
        OrchestratorState.COMPLETED: [],  # Terminal
        OrchestratorState.FAILED: [],     # Terminal
        OrchestratorState.ABORTED: [],    # Terminal
    }
    
    def __init__(self):
        self.current_state = OrchestratorState.INIT
        self.state_history: list[StateTransition] = []
    
    def transition_to(
        self,
        to_state: OrchestratorState,
        reason: str = "",
        context_data: Optional[Dict[str, Any]] = None,
    ) -> StateTransition:
        """
        Transition to a new state
        
        Args:
            to_state: Target state
            reason: Reason for transition
            context_data: Optional context data
        
        Returns:
            StateTransition object
        
        Raises:
            ValueError: If transition is invalid
        """
        from_state = self.current_state
        
        # Validate transition
        if to_state not in self.VALID_TRANSITIONS.get(from_state, []):
            raise ValueError(
                f"Invalid transition from {from_state.value} to {to_state.value}"
            )
        
        # Record transition
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            timestamp=datetime.utcnow().isoformat() + "Z",
            context_data=context_data,
        )
        
        self.state_history.append(transition)
        self.current_state = to_state
        
        logger.info(f"State transition: {from_state.value} -> {to_state.value} ({reason})")
        return transition
    
    def is_terminal(self) -> bool:
        """Check if current state is terminal"""
        return self.current_state in [
            OrchestratorState.COMPLETED,
            OrchestratorState.FAILED,
            OrchestratorState.ABORTED,
        ]
    
    def can_transition_to(self, to_state: OrchestratorState) -> bool:
        """Check if transition to target state is valid"""
        return to_state in self.VALID_TRANSITIONS.get(self.current_state, [])
    
    def get_state_history(self) -> list[StateTransition]:
        """Get the state transition history"""
        return self.state_history.copy()
