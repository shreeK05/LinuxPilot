import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db
from app.db.base_class import Base

# Setup in-memory sqlite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override
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

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "LinuxPilot API"}

def test_create_task():
    response = client.post(
        "/api/v1/tasks/",
        json={"goal": "Test Task", "risk_level": 0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["goal"] == "Test Task"
    assert "id" in data

def test_get_tasks():
    client.post("/api/v1/tasks/", json={"goal": "Test Task 1", "risk_level": 1})
    client.post("/api/v1/tasks/", json={"goal": "Test Task 2", "risk_level": 0})
    
    response = client.get("/api/v1/tasks/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(task["goal"] == "Test Task 1" for task in data)
