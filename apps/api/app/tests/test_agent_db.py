import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
from app.repositories.agent_repo import save_plan, update_task_state
from app.models.domain import Task, PlanStep
from app.agent.models import ExecutionPlan, PlanStep as AgentPlanStep, ActionDefinition, AgentState, GoalUnderstanding
from app.agent.orchestrator import AgentOrchestrator
from app.agent.context import ExecutionContext
from app.agent.planner import DeterministicPlanner

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_agent_repo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_duplicate_logical_step_id_saved_successfully():
    db = TestingSessionLocal()

    # 1. Create two tasks
    task1 = Task(id="task-1", goal="Goal 1")
    task2 = Task(id="task-2", goal="Goal 2")
    db.add(task1)
    db.add(task2)
    db.commit()

    # 2. Both tasks generate the exact same plan with the exact same step IDs
    planner = DeterministicPlanner()
    goal = GoalUnderstanding(intent="Test", objective="Find all PDF files", entities=[], constraints=[], preconditions=[], expected_outcome="", risk_assessment="", required_permissions=[], relevant_context="")
    plan1 = planner.create_plan(goal)
    plan2 = planner.create_plan(goal)

    # Force step IDs to be identical logically
    assert plan1.steps[0].step_id == "step-fallback"
    assert plan2.steps[0].step_id == "step-fallback"

    # 3. Save both plans (Should NOT raise IntegrityError because of the `<plan_id>_` prefix)
    save_plan(db, "task-1", plan1)
    save_plan(db, "task-2", plan2)

    # 4. Verify in DB that they have composite IDs
    db_steps = db.query(PlanStep).all()
    assert len(db_steps) == 2
    assert db_steps[0].id == f"{plan1.plan_id}_step-fallback"
    assert db_steps[1].id == f"{plan2.plan_id}_step-fallback"

    db.close()

def test_database_failure_transition_to_failed():
    db = TestingSessionLocal()
    task1 = Task(id="task-3", goal="Error Goal", status="PLANNING")
    db.add(task1)
    db.commit()

    plan = ExecutionPlan(plan_id="bad-plan", steps=[
        AgentPlanStep(step_id="step1", name="Step 1", dependencies=[], action=ActionDefinition(action_type="test.action", parameters={}))
    ])

    # Intentionally cause a DB error in save_plan by dropping tables
    Base.metadata.drop_all(bind=engine)

    try:
        save_plan(db, "task-3", plan)
    except Exception:
        # Re-create tables so we can test the update_task_state rollback logic
        Base.metadata.create_all(bind=engine)
        db.add(Task(id="task-3", goal="Error Goal", status="PLANNING"))
        db.commit()

        # update_task_state should succeed because the session was rolled back in save_plan
        update_task_state(db, "task-3", AgentState.FAILED)

    updated_task = db.query(Task).filter(Task.id == "task-3").first()
    assert updated_task.status == "FAILED"

    db.close()

def test_context_passing_still_resolving_logical_step_ids():
    orchestrator = AgentOrchestrator(
        context=ExecutionContext(task_id="test"),
        interpreter=None, planner=None, policy_engine=None,
        execution_engine=None, verifier=None, recovery_engine=None
    )

    # The output from step-fallback is stored under logical step_id
    orchestrator.step_outputs = {
        "step-fallback": {"result": "success data"}
    }

    params = {
        "input": "{{step-fallback.output.result}}"
    }

    resolved = orchestrator._interpolate_parameters(params)
    assert resolved["input"] == "success data"
