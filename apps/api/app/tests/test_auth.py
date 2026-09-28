import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db
from app.models.domain import User
from app.db.base_class import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
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

    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_register_user():
    # Clean up existing user if any
    db = TestingSessionLocal()
    db.query(User).filter(User.username == "testuser").delete()
    db.commit()
    db.close()

    response = client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data

def test_login_user():
    client.post("/api/v1/auth/register", json={"username": "testuser", "password": "testpassword"})
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_me():
    # Login to get token
    client.post("/api/v1/auth/register", json={"username": "testuser", "password": "testpassword"})
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    token = response.json()["access_token"]

    # Request me
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

def test_protected_route_without_token():
    response = client.get("/api/v1/tasks/")
    assert response.status_code == 401
