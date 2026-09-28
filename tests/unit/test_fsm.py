"""
Unit Tests: Orchestrator FSM
Tests for state machine transitions and validation
"""

import pytest
from linuxpilot.orchestrator.fsm import OrchestratorFSM, OrchestratorState


@pytest.fixture
def fsm():
    return OrchestratorFSM()


class TestFSMTransitions:
    """Test valid and invalid state transitions"""

    def test_initial_state(self, fsm):
        assert fsm.current_state == OrchestratorState.INIT

    def test_valid_transition(self, fsm):
        transition = fsm.transition_to(OrchestratorState.PLANNING, "Start planning")
        assert fsm.current_state == OrchestratorState.PLANNING
        assert transition.from_state == OrchestratorState.INIT
        assert transition.to_state == OrchestratorState.PLANNING

    def test_invalid_transition_raises(self, fsm):
        with pytest.raises(ValueError, match="Invalid transition"):
            fsm.transition_to(OrchestratorState.EXECUTING)

    def test_full_happy_path(self, fsm):
        fsm.transition_to(OrchestratorState.PLANNING)
        fsm.transition_to(OrchestratorState.POLICY_CHECK)
        fsm.transition_to(OrchestratorState.READY)
        fsm.transition_to(OrchestratorState.EXECUTING)
        fsm.transition_to(OrchestratorState.VERIFYING)
        fsm.transition_to(OrchestratorState.EXECUTING)
        assert fsm.current_state == OrchestratorState.EXECUTING

    def test_terminal_state_no_transitions(self, fsm):
        fsm.transition_to(OrchestratorState.PLANNING)
        fsm.transition_to(OrchestratorState.FAILED)
        assert fsm.is_terminal()
        with pytest.raises(ValueError):
            fsm.transition_to(OrchestratorState.PLANNING)

    def test_rollback_path(self, fsm):
        fsm.transition_to(OrchestratorState.PLANNING)
        fsm.transition_to(OrchestratorState.POLICY_CHECK)
        fsm.transition_to(OrchestratorState.READY)
        fsm.transition_to(OrchestratorState.EXECUTING)
        fsm.transition_to(OrchestratorState.ROLLING_BACK)
        assert fsm.current_state == OrchestratorState.ROLLING_BACK

    def test_approval_path(self, fsm):
        fsm.transition_to(OrchestratorState.PLANNING)
        fsm.transition_to(OrchestratorState.POLICY_CHECK)
        fsm.transition_to(OrchestratorState.WAITING_APPROVAL)
        fsm.transition_to(OrchestratorState.READY)
        assert fsm.current_state == OrchestratorState.READY

    def test_state_history(self, fsm):
        fsm.transition_to(OrchestratorState.PLANNING)
        fsm.transition_to(OrchestratorState.FAILED)
        history = fsm.get_state_history()
        assert len(history) == 2

    def test_can_transition_to(self, fsm):
        assert fsm.can_transition_to(OrchestratorState.PLANNING)
        assert not fsm.can_transition_to(OrchestratorState.EXECUTING)

    def test_is_terminal(self, fsm):
        assert not fsm.is_terminal()
        fsm.transition_to(OrchestratorState.PLANNING)
        fsm.transition_to(OrchestratorState.FAILED)
        assert fsm.is_terminal()
