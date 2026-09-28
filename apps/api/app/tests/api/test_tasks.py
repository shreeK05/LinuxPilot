from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest
from app.main import app
from app.db.session import get_db
from app.db.base_class import Base
from app.models.domain import Task, Plan, PlanStep, AuditEvent, ActionExecution, Verification
from app.agent.models import AgentState
from datetime import datetime, timezone
import uuid

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_tasks_plan.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    def override_get_current_user():
        from app.models.domain import User
        return User(id="test-user-id", username="testuser")

    app.dependency_overrides[get_db] = override_get_db
    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_get_task_plan_not_found():
    response = client.get("/api/v1/tasks/invalid-id/plan")
    assert response.status_code == 404

def test_get_task_plan_no_plan(db_session):
    task = Task(id="task-1", user_id="test-user-id", goal="Goal 1", status=AgentState.EXECUTING.value)
    db_session.add(task)
    db_session.commit()
    
    response = client.get("/api/v1/tasks/task-1/plan")
    assert response.status_code == 200
    assert response.json() is None

def test_get_task_plan_completed_success(db_session):
    task = Task(id="task-comp", user_id="test-user-id", goal="Goal 2", status=AgentState.COMPLETED.value)
    plan = Plan(id="plan-1", task_id="task-comp", version=1, status="ACTIVE")
    step = PlanStep(
        id="plan-1_step_1", 
        plan_id="plan-1", 
        sequence=0, 
        name="Step 1", 
        action_type="command", 
        parameters={"cmd": "ls"}, 
        risk_level=1, 
        dependencies=[]
    )
    # AuditEvent records (how the real orchestrator writes execution state)
    action_completed_event = AuditEvent(
        id="evt-1",
        task_id="task-comp",
        event_type="ACTION_COMPLETED",
        actor="System",
        payload={"step_id": "step_1", "output": {"stdout": "file1.txt"}, "status": "SUCCESS"}
    )
    verification_completed_event = AuditEvent(
        id="evt-2",
        task_id="task-comp",
        event_type="VERIFICATION_COMPLETED",
        actor="System",
        payload={"step_id": "step_1", "success": True, "expected_state": {"file": "file1.txt"}, "actual_state": {"file": "file1.txt"}, "status": "SUCCESS"}
    )
    
    db_session.add_all([task, plan, step, action_completed_event, verification_completed_event])
    db_session.commit()

    response = client.get("/api/v1/tasks/task-comp/plan")
    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "plan-1"
    assert len(data["steps"]) == 1
    
    step_data = data["steps"][0]
    assert step_data["logical_step_id"] == "step_1"
    assert step_data["status"] == "SUCCESS"
    assert step_data["result"] == {"stdout": "file1.txt"}
    assert step_data["verification"]["passed"] is True
    assert step_data["verification"]["expected"] == {"file": "file1.txt"}

def test_get_task_plan_not_executed_or_verified(db_session):
    task = Task(id="task-fail", user_id="test-user-id", goal="Goal 3", status=AgentState.FAILED.value)
    plan = Plan(id="plan-2", task_id="task-fail", version=1, status="ACTIVE")
    step = PlanStep(
        id="plan-2_step_1", 
        plan_id="plan-2", 
        sequence=0, 
        name="Step 1", 
        action_type="command", 
        parameters={"cmd": "ls"}, 
        risk_level=1, 
        dependencies=[]
    )
    
    db_session.add_all([task, plan, step])
    db_session.commit()

    response = client.get("/api/v1/tasks/task-fail/plan")
    assert response.status_code == 200
    data = response.json()
    
    step_data = data["steps"][0]
    assert step_data["status"] == "Not executed"
    assert step_data["result"] is None
    assert step_data["verification"] == "Not verified"
