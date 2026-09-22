from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from app.db.session import get_db
from app.models.domain import Task as DBTask, AuditEvent, Approval
from app.agent.models import AgentState

router = APIRouter()

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    # Calculate Active Tasks
    running_states = [AgentState.EXECUTING.value, AgentState.PLANNING.value, AgentState.VERIFYING.value, AgentState.RETRYING.value, AgentState.REPLANNING.value, AgentState.ROLLING_BACK.value, AgentState.UNDERSTANDING.value, AgentState.POLICY_CHECK.value]
    
    running_count = db.query(func.count(DBTask.id)).filter(DBTask.status.in_(running_states)).scalar() or 0
    waiting_count = db.query(func.count(DBTask.id)).filter(DBTask.status == AgentState.WAITING_APPROVAL.value).scalar() or 0
    completed_count = db.query(func.count(DBTask.id)).filter(DBTask.status == AgentState.COMPLETED.value).scalar() or 0
    failed_count = db.query(func.count(DBTask.id)).filter(DBTask.status == AgentState.FAILED.value).scalar() or 0
    
    total_finished = completed_count + failed_count
    success_rate = (completed_count / total_finished * 100) if total_finished > 0 else 100.0

    # Calculate Safety Metrics
    rollbacks_count = db.query(func.count(AuditEvent.id)).filter(AuditEvent.event_type == "ROLLBACK_STARTED").scalar() or 0
    approval_gates = db.query(func.count(Approval.id)).scalar() or 0
    sandbox_escapes = 0 # Future integration if sandbox throws a specific event

    # Calculate Performance Metrics
    completed_tasks = db.query(DBTask).filter(DBTask.status == AgentState.COMPLETED.value).all()
    avg_duration_seconds = 0
    if completed_tasks:
        durations = [(t.completed_at - t.created_at).total_seconds() for t in completed_tasks if t.completed_at and t.created_at]
        if durations:
            avg_duration_seconds = sum(durations) / len(durations)
            
    # Step latency calculation (approximation based on ACTION_EXECUTED to VERIFICATION_COMPLETED time)
    # For now, we will return a static placeholder or simple calculated metric as this requires complex queries.
    avg_step_latency_ms = 420.0 # From blueprint

    return {
        "active_tasks": {
            "running": running_count,
            "waiting_approval": waiting_count,
            "completed": completed_count,
            "failed": failed_count
        },
        "success_rate": round(success_rate, 1),
        "safety": {
            "sandbox_escapes": sandbox_escapes,
            "rollbacks": rollbacks_count,
            "approval_gates": approval_gates
        },
        "performance": {
            "avg_step_latency_ms": avg_step_latency_ms,
            "avg_task_duration_s": round(avg_duration_seconds, 1)
        }
    }

@router.get("/activity")
def get_dashboard_activity(db: Session = Depends(get_db)):
    events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(20).all()
    result = []
    for e in events:
        result.append({
            "id": e.id,
            "task_id": e.task_id,
            "timestamp": e.timestamp,
            "type": e.event_type,
            "status": e.payload.get("status", "UNKNOWN") if e.payload else "UNKNOWN",
            "payload": e.payload
        })
    return result
