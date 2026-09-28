import uuid
from typing import Any
from sqlalchemy.orm import as_declarative, declared_attr, relationship
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey
from datetime import datetime, timezone
from app.db.base_class import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    settings = Column(JSON, default=dict)

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'))
    goal = Column(Text, nullable=False)
    status = Column(String, default="PENDING")
    risk_level = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    plans = relationship("Plan", backref="task", cascade="all, delete-orphan")

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey('tasks.id'))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    event_type = Column(String)
    actor = Column(String)
    payload = Column(JSON)

class Execution(Base):
    __tablename__ = 'executions'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey('tasks.id'))
    worker_id = Column(String)
    status = Column(String)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

class Plan(Base):
    __tablename__ = 'plans'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey('tasks.id'))
    version = Column(Integer, default=1)
    status = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    steps = relationship("PlanStep", backref="plan", cascade="all, delete-orphan", order_by="PlanStep.sequence")

class Snapshot(Base):
    __tablename__ = 'snapshots'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey('tasks.id'))
    action_id = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    snapshot_path = Column(String, nullable=True)
    original_hash = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    operation_type = Column(String, nullable=False)
    restoration_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class PlanStep(Base):
    __tablename__ = 'plan_steps'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String, ForeignKey('plans.id'))
    sequence = Column(Integer)
    name = Column(String)
    action_type = Column(String)
    parameters = Column(JSON)
    risk_level = Column(Integer)
    status = Column(String)
    dependencies = Column(JSON, default=list)

class ActionExecution(Base):
    __tablename__ = 'action_executions'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String, ForeignKey('executions.id'))
    step_id = Column(String, ForeignKey('plan_steps.id'))
    input_data = Column(JSON)
    output_data = Column(JSON)
    status = Column(String)
    latency_ms = Column(Integer)

class Approval(Base):
    __tablename__ = 'approvals'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey('tasks.id'))
    plan_id = Column(String, ForeignKey('plans.id'), nullable=True)
    action_id = Column(String, nullable=False)
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    risk_level = Column(Integer)
    reason = Column(String)
    status = Column(String)
    decision_at = Column(DateTime, nullable=True)
    decision_source = Column(String, nullable=True)
    action_parameters = Column(JSON, nullable=True)

class Verification(Base):
    __tablename__ = 'verifications'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action_execution_id = Column(String, ForeignKey('action_executions.id'))
    expected_state = Column(JSON)
    actual_state = Column(JSON)
    result = Column(String)
    confidence = Column(Float)
