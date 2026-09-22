from sqlalchemy.orm import Session
from app.models.domain import Task, Plan, PlanStep, Execution, ActionExecution, AuditEvent
from app.agent.models import AgentState, ExecutionPlan, PlanStep as AgentPlanStep, StateTransition
from app.agent.context import ExecutionContext

def get_task(db: Session, task_id: str) -> Task:
    return db.query(Task).filter(Task.id == task_id).first()

def update_task_state(db: Session, task_id: str, state: AgentState):
    from datetime import datetime
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = state.value
            if state in (AgentState.COMPLETED, AgentState.FAILED, AgentState.CANCELLED):
                task.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(task)
    except Exception:
        db.rollback()
        raise


def create_approval(db: Session, transition: StateTransition, context: ExecutionContext):
    from app.models.domain import Approval
    import uuid
    # Check if pending already exists to avoid duplicates
    existing = db.query(Approval).filter(
        Approval.task_id == context.task_id,
        Approval.status == "PENDING"
    ).first()
    if not existing:
        new_approval = Approval(
            id=str(uuid.uuid4()),
            task_id=context.task_id,
            plan_id=context.plan_id,
            action_id="plan_approval",
            risk_level=transition.context_data.get("risk_level", 0) if transition.context_data else 0,
            reason=transition.reason,
            status="PENDING"
        )
        db.add(new_approval)
        db.commit()

def save_plan(db: Session, task_id: str, plan: ExecutionPlan):
    try:
        # Archive previous active plans for this task and find max version
        previous_plans = db.query(Plan).filter(Plan.task_id == task_id, Plan.status == "ACTIVE").all()
        max_version = 0

        # Get highest version
        all_plans = db.query(Plan).filter(Plan.task_id == task_id).all()
        for p in all_plans:
            if p.version > max_version:
                max_version = p.version

        for p in previous_plans:
            p.status = "ARCHIVED"

        db_plan = Plan(id=plan.plan_id, task_id=task_id, version=max_version + 1, status="ACTIVE")
        db.add(db_plan)

        for i, step in enumerate(plan.steps):
            db_step = PlanStep(
                id=f"{plan.plan_id}_{step.step_id}",
                plan_id=plan.plan_id,
                sequence=i,
                name=step.name,
                dependencies=[f"{plan.plan_id}_{d}" for d in step.dependencies],
                action_type=step.action.action_type,
                parameters=step.action.parameters,
                risk_level=step.action.risk_level.value
            )
            db.add(db_step)
        db.commit()
    except Exception:
        db.rollback()
        raise

def log_audit_event(db: Session, task_id: str, event_type: str, status: str, payload: dict):
    try:
        # status could be part of payload or combined
        payload["status"] = status
        event = AuditEvent(
            task_id=task_id,
            event_type=event_type,
            actor="System",
            payload=payload
        )
        db.add(event)
        db.commit()
    except Exception:
        db.rollback()
        raise

def get_audit_events(db: Session, task_id: str):
    return db.query(AuditEvent).filter(AuditEvent.task_id == task_id).order_by(AuditEvent.timestamp).all()
