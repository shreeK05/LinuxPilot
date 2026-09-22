from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest
from app.main import app
from app.db.session import get_db
from app.db.base_class import Base
from app.models.domain import Task, AuditEvent, Approval
from app.agent.models import AgentState
from datetime import datetime, timezone
import json

# Setup in-memory sqlite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_dashboard.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_dashboard_stats(db_session):
    # Setup mock data
    task1 = Task(id="task-1", goal="Goal 1", risk_level=1, status=AgentState.EXECUTING.value, created_at=datetime.now(timezone.utc))
    task2 = Task(id="task-2", goal="Goal 2", risk_level=2, status=AgentState.WAITING_APPROVAL.value, created_at=datetime.now(timezone.utc))
    task3 = Task(id="task-3", goal="Goal 3", risk_level=1, status=AgentState.COMPLETED.value, created_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc))
    
    audit1 = AuditEvent(id="audit-1", task_id="task-1", timestamp=datetime.now(timezone.utc), event_type="ACTION_EXECUTED", payload={})
    audit2 = AuditEvent(id="audit-2", task_id="task-1", timestamp=datetime.now(timezone.utc), event_type="ROLLBACK_STARTED", payload={})
    
    approval1 = Approval(id="appr-1", task_id="task-2", action_id="act-1", requested_at=datetime.now(timezone.utc), status="PENDING")
    
    db_session.add(task1)
    db_session.add(task2)
    db_session.add(task3)
    db_session.add(audit1)
    db_session.add(audit2)
    db_session.add(approval1)
    db_session.commit()

    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert data["active_tasks"]["running"] >= 1
    assert data["active_tasks"]["waiting_approval"] >= 1
    assert data["active_tasks"]["completed"] >= 1
    assert data["success_rate"] == 100.0 # 1 completed, 0 failed
    
    assert data["safety"]["rollbacks"] >= 1
    assert data["safety"]["approval_gates"] >= 1

def test_dashboard_activity(db_session):
    audit1 = AuditEvent(id="audit-1", task_id="task-1", timestamp=datetime.now(timezone.utc), event_type="ACTION_EXECUTED", payload={})
    audit2 = AuditEvent(id="audit-2", task_id="task-1", timestamp=datetime.now(timezone.utc), event_type="ROLLBACK_STARTED", payload={})
    db_session.add(audit1)
    db_session.add(audit2)
    db_session.commit()

    response = client.get("/api/v1/dashboard/activity")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2 # From setup above
    assert data[0]["type"] in ["ACTION_EXECUTED", "ROLLBACK_STARTED"]
