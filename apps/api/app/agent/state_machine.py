from datetime import datetime
from typing import Dict, List, Optional
from app.agent.models import AgentState, StateTransition

class StateMachineError(Exception):
    pass

class AgentStateMachine:
    VALID_TRANSITIONS: Dict[AgentState, List[AgentState]] = {
        AgentState.IDLE: [AgentState.UNDERSTANDING, AgentState.CANCELLED],
        AgentState.UNDERSTANDING: [AgentState.PLANNING, AgentState.FAILED, AgentState.CANCELLED],
        AgentState.PLANNING: [AgentState.POLICY_CHECK, AgentState.FAILED, AgentState.CANCELLED],
        AgentState.POLICY_CHECK: [AgentState.WAITING_APPROVAL, AgentState.READY, AgentState.FAILED, AgentState.CANCELLED],
        AgentState.WAITING_APPROVAL: [AgentState.READY, AgentState.FAILED, AgentState.CANCELLED],
        AgentState.READY: [AgentState.EXECUTING, AgentState.CANCELLED],
        AgentState.EXECUTING: [AgentState.VERIFYING, AgentState.COMPLETED, AgentState.FAILED, AgentState.CANCELLED, AgentState.RETRYING, AgentState.REPLANNING, AgentState.ROLLING_BACK],
        AgentState.VERIFYING: [AgentState.COMPLETED, AgentState.EXECUTING, AgentState.RETRYING, AgentState.REPLANNING, AgentState.ROLLING_BACK, AgentState.FAILED],
        AgentState.RETRYING: [AgentState.EXECUTING, AgentState.FAILED, AgentState.CANCELLED],
        AgentState.REPLANNING: [AgentState.PLANNING, AgentState.POLICY_CHECK, AgentState.FAILED, AgentState.CANCELLED],
        AgentState.ROLLING_BACK: [AgentState.FAILED, AgentState.COMPLETED],
        # Terminal states
        AgentState.COMPLETED: [],
        AgentState.FAILED: [],
        AgentState.CANCELLED: []
    }
    
    # We need to map some states dynamically or allow recovery states, let's fix the above list based on recovery states:
    # Adding RECOVERY_REQUIRED to the Enum would be good, but wait, RECOVERY is not in AgentState. Let me check what I put in models.py.
    # Models.py has RETRYING, REPLANNING, ROLLING_BACK.
    
    def __init__(self, initial_state: AgentState = AgentState.IDLE):
        self.current_state = initial_state
        self.history: List[StateTransition] = []

    def transition_to(self, new_state: AgentState, reason: Optional[str] = None, context: Optional[dict] = None) -> StateTransition:
        if new_state not in self.get_valid_next_states():
            raise StateMachineError(f"Invalid transition from {self.current_state} to {new_state}")
        
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            reason=reason,
            context_data=context
        )
        self.history.append(transition)
        self.current_state = new_state
        return transition

    def get_valid_next_states(self) -> List[AgentState]:
        return self.VALID_TRANSITIONS.get(self.current_state, [])

    def is_terminal(self) -> bool:
        return self.current_state in [AgentState.COMPLETED, AgentState.FAILED, AgentState.CANCELLED]
