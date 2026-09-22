import pytest
from app.agent.orchestrator import AgentOrchestrator
from app.agent.models import AgentState, GoalUnderstanding, ExecutionPlan, PlanStep, ActionDefinition, RiskLevel, RecoveryDecisionResult, PolicyDecisionResult
from app.agent.context import ExecutionContext

# We will mock the pieces to test the orchestrator loop explicitly.

class MockInterpreter:
    def interpret(self, raw_goal: str) -> GoalUnderstanding:
        return GoalUnderstanding(intent="test", objective="test", entities=[], expected_outcome="mock", risk_assessment="mock")

class MockPlanner:
    def __init__(self):
        self.replan_called = 0
        self.last_failed_step = None
        self.last_executed_steps = []

    def create_plan(self, goal: GoalUnderstanding) -> ExecutionPlan:
        step1 = PlanStep(
            step_id="step1",
            name="Step 1",
            dependencies=[],
            action=ActionDefinition(action_type="test.action", parameters={}, risk_level=RiskLevel.LEVEL_0_READ_ONLY)
        )
        return ExecutionPlan(plan_id="plan1", steps=[step1], risk_level=RiskLevel.LEVEL_0_READ_ONLY)

    def replan(self, goal: GoalUnderstanding, current_plan: ExecutionPlan, failed_step: PlanStep, error: str, executed_steps: list) -> ExecutionPlan:
        self.replan_called += 1
        self.last_failed_step = failed_step.step_id
        self.last_executed_steps = executed_steps
        
        step2 = PlanStep(
            step_id="step2",
            name="Step 2 (Replanned)",
            dependencies=[],
            action=ActionDefinition(action_type="test.replanned", parameters={}, risk_level=RiskLevel.LEVEL_0_READ_ONLY)
        )
        return ExecutionPlan(plan_id=f"plan_{self.replan_called + 1}", steps=[step2], risk_level=RiskLevel.LEVEL_0_READ_ONLY)

class MockPolicyEngine:
    def __init__(self):
        self.evaluate_calls = 0
    def evaluate(self, action):
        self.evaluate_calls += 1
        class MockDecision:
            decision = PolicyDecisionResult.ALLOW
            risk_level = action.risk_level
            reason = "ok"
            def model_dump(self): return {}
        return MockDecision()

class MockExecutionEngine:
    def __init__(self):
        self.execute_calls = 0
    def execute_action(self, action):
        self.execute_calls += 1
        class MockResult:
            success = False
            output = None
            error = "Mock Failure"
        return MockResult()

class MockVerifier:
    def verify(self, action, output):
        class MockVerify:
            success = False
            error = "Mock Verification Failure"
            def model_dump(self): return {}
        return MockVerify()

class MockRecoveryEngine:
    def determine_recovery(self, action, error, retries, verification_result=None):
        class MockDecision:
            decision = RecoveryDecisionResult.REPLAN
            reason = "Must replan"
            def model_dump(self): return {}
        return MockDecision()

def test_replanning_loop_and_max_replans():
    context = ExecutionContext(task_id="task1", user_id="user1")
    interpreter = MockInterpreter()
    planner = MockPlanner()
    policy = MockPolicyEngine()
    execution = MockExecutionEngine()
    verifier = MockVerifier()
    recovery = MockRecoveryEngine()
    
    orchestrator = AgentOrchestrator(
        context=context,
        interpreter=interpreter,
        planner=planner,
        policy_engine=policy,
        execution_engine=execution,
        verifier=verifier,
        recovery_engine=recovery
    )
    
    # We expect the task to fail completely after max_replans (2) are exhausted.
    orchestrator.run_lifecycle("do something")
    
    # It should have called replan twice
    assert planner.replan_called == 2
    
    # It should have executed 3 times total (original + 2 replans)
    assert execution.execute_calls == 3
    
    # Policy should have evaluated 3 plans (original + 2 replans)
    assert policy.evaluate_calls == 3
    
    # Final state should be FAILED
    assert orchestrator.state_machine.current_state == AgentState.FAILED

def test_replan_preserves_executed_steps():
    context = ExecutionContext(task_id="task2", user_id="user1")
    planner = MockPlanner()
    
    # Custom Execution Engine that succeeds on step1 but fails on step2
    class CustomExecutionEngine:
        def execute_action(self, action):
            class MockResult:
                success = (action.action_type == "test.success")
                output = "ok" if success else None
                error = None if success else "failed"
            return MockResult()
            
    class CustomPlanner(MockPlanner):
        def create_plan(self, goal):
            step1 = PlanStep(
                step_id="step1", name="Success Step", dependencies=[],
                action=ActionDefinition(action_type="test.success", parameters={}, risk_level=RiskLevel.LEVEL_0_READ_ONLY)
            )
            step2 = PlanStep(
                step_id="step2", name="Fail Step", dependencies=["step1"],
                action=ActionDefinition(action_type="test.fail", parameters={}, risk_level=RiskLevel.LEVEL_0_READ_ONLY)
            )
            return ExecutionPlan(plan_id="plan1", steps=[step1, step2], risk_level=RiskLevel.LEVEL_0_READ_ONLY)

    custom_planner = CustomPlanner()
    execution = CustomExecutionEngine()
    
    class CustomVerifier:
        def verify(self, action, output):
            class MockVerify:
                success = (action.action_type == "test.success")
                error = None if success else "Mock Verification Failure"
                def model_dump(self): return {}
                def model_dump_json(self, indent=2): return "{}"
            return MockVerify()
            
    class CustomRecovery:
        def determine_recovery(self, action, error, retries, vr=None):
            class MockDecision:
                decision = RecoveryDecisionResult.REPLAN if action.action_type == "test.fail" else RecoveryDecisionResult.FAIL
                reason = "replan"
                def model_dump(self): return {}
            return MockDecision()

    orchestrator = AgentOrchestrator(
        context=context,
        interpreter=MockInterpreter(),
        planner=custom_planner,
        policy_engine=MockPolicyEngine(),
        execution_engine=execution,
        verifier=CustomVerifier(),
        recovery_engine=CustomRecovery()
    )  
    orchestrator.run_lifecycle("test")
    
    # Step1 should be passed in executed_steps to replanner!
    assert custom_planner.last_executed_steps == ["step1"]
    assert custom_planner.last_failed_step == "step2"
