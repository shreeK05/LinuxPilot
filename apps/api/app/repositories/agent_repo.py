from sqlalchemy.orm import Session
from app.models.domain import Task, Plan, PlanStep, Execution, ActionExecution, AuditEvent
from app.agent.models import AgentState, ExecutionPlan, PlanStep as AgentPlanStep, StateTransition
from app.agent.context import ExecutionContext

def get_task(db: Session, task_id: str) -> Task:
    return db.query(Task).filter(Task.id == task_id).first()

def update_task_state(db: Session, task_id: str, state: AgentState):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task.status = state.value
        db.commit()

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
    db_plan = Plan(id=plan.plan_id, task_id=task_id)
    db.add(db_plan)
    
    for i, step in enumerate(plan.steps):
        db_step = PlanStep(
            id=step.step_id,
            plan_id=plan.plan_id,
            sequence=i,
            name=step.name,
            dependencies=step.dependencies,
            action_type=step.action.action_type,
            parameters=step.action.parameters,
            risk_level=step.action.risk_level.value
        )
        db.add(db_step)
    db.commit()

def log_audit_event(db: Session, task_id: str, event_type: str, status: str, payload: dict):
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

def get_audit_events(db: Session, task_id: str):
    return db.query(AuditEvent).filter(AuditEvent.task_id == task_id).order_by(AuditEvent.timestamp).all()
