import pytest
from app.agent.models import AgentState, ActionDefinition, PlanStep, RiskLevel
from app.agent.state_machine import AgentStateMachine, StateMachineError
from app.agent.planner import DAGValidator, PlannerError
from app.agent.policy import PolicyEngine
from app.agent.actions.registry import action_registry
from app.agent.executor import ExecutionEngine
from app.agent.verifier import DeterministicVerifier
from app.agent.recovery import RecoveryEngine
from app.agent.context import ExecutionContext
from app.agent.orchestrator import AgentOrchestrator
from app.agent.goal_understanding import DeterministicGoalInterpreter
from app.agent.planner import DeterministicPlanner

def test_state_machine_valid_transition():
    sm = AgentStateMachine()
    assert sm.current_state == AgentState.IDLE
    sm.transition_to(AgentState.UNDERSTANDING)
    assert sm.current_state == AgentState.UNDERSTANDING

def test_state_machine_invalid_transition():
    sm = AgentStateMachine()
    with pytest.raises(StateMachineError):
        sm.transition_to(AgentState.EXECUTING) # Cannot go IDLE -> EXECUTING

def test_dag_validator_valid():
    step1 = PlanStep(step_id="1", name="A", action=ActionDefinition(action_type="test.init", parameters={}))
    step2 = PlanStep(step_id="2", name="B", dependencies=["1"], action=ActionDefinition(action_type="test.init", parameters={}))
    sorted_steps = DAGValidator.topological_sort([step2, step1])
    assert sorted_steps[0].step_id == "1"
    assert sorted_steps[1].step_id == "2"

def test_dag_validator_cycle():
    step1 = PlanStep(step_id="1", name="A", dependencies=["2"], action=ActionDefinition(action_type="test.init", parameters={}))
    step2 = PlanStep(step_id="2", name="B", dependencies=["1"], action=ActionDefinition(action_type="test.init", parameters={}))
    with pytest.raises(PlannerError):
        DAGValidator.topological_sort([step1, step2])

def test_policy_engine_allow():
    engine = PolicyEngine()
    action = ActionDefinition(action_type="test", parameters={}, risk_level=RiskLevel.LEVEL_1_NON_DESTRUCTIVE)
    decision = engine.evaluate(action)
    assert decision.decision == "ALLOW"

def test_policy_engine_block():
    engine = PolicyEngine()
    action = ActionDefinition(action_type="test", parameters={}, risk_level=RiskLevel.LEVEL_5_BLOCKED)
    decision = engine.evaluate(action)
    assert decision.decision == "BLOCK"

def test_orchestrator_lifecycle():
    context = ExecutionContext(task_id="test_task")
    orchestrator = AgentOrchestrator(
        context=context,
        interpreter=DeterministicGoalInterpreter(),
        planner=DeterministicPlanner(),
        policy_engine=PolicyEngine(),
        execution_engine=ExecutionEngine(action_registry, PolicyEngine()),
        verifier=DeterministicVerifier(),
        recovery_engine=RecoveryEngine()
    )
    
    orchestrator.run_lifecycle("Download PDF files")
    
    assert orchestrator.state_machine.current_state == AgentState.COMPLETED
    assert orchestrator.goal.expected_outcome == "A list of all PDF files located in the Downloads directory."
    assert orchestrator.plan is not None
    assert len(orchestrator.plan.steps) == 4
