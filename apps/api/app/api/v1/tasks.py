from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.session import get_db
from app.models.domain import Task as DBTask
from app.schemas.task import TaskCreate, TaskResponse
from app.repositories.agent_repo import update_task_state, create_approval, save_plan, log_audit_event, get_audit_events
from app.agent.orchestrator import AgentOrchestrator
from app.agent.goal_understanding import DeterministicGoalInterpreter
from app.agent.planner import DeterministicPlanner
from app.agent.policy import PolicyEngine
from app.agent.executor import ExecutionEngine
from app.agent.verifier import DeterministicVerifier
from app.agent.recovery import RecoveryEngine
from app.agent.context import ExecutionContext
from app.agent.actions.registry import action_registry
from app.agent.models import AgentState

from app.db.session import SessionLocal

router = APIRouter()

def run_agent_lifecycle(task_id: str, goal: str):
    # Setup context
    context = ExecutionContext(task_id=task_id)
    
    db = SessionLocal()
    try:
        # State change callback
        def on_state_change(transition, ctx):
            update_task_state(db, ctx.task_id, transition.to_state)
            if transition.to_state == AgentState.WAITING_APPROVAL:
                create_approval(db, transition, ctx)
            
        # Audit callback
        def on_audit_event(event_type, status, metadata, ctx):
            log_audit_event(db, ctx.task_id, event_type, status, metadata)

        # Assemble components
        interpreter = DeterministicGoalInterpreter()
        planner = DeterministicPlanner()
        policy_engine = PolicyEngine()
        execution_engine = ExecutionEngine(action_registry, policy_engine)
        verifier = DeterministicVerifier()
        recovery_engine = RecoveryEngine()

        orchestrator = AgentOrchestrator(
            context=context,
            interpreter=interpreter,
            planner=planner,
            policy_engine=policy_engine,
            execution_engine=execution_engine,
            verifier=verifier,
            recovery_engine=recovery_engine,
            on_state_change=on_state_change,
            on_audit_event=on_audit_event
        )
        
        original_create_plan = orchestrator.planner.create_plan
        def intercepted_create_plan(goal_under):
            plan = original_create_plan(goal_under)
            save_plan(db, task_id, plan)
            return plan
        orchestrator.planner.create_plan = intercepted_create_plan

        orchestrator.run_lifecycle(goal)
    finally:
        db.close()


@router.post("/", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = DBTask(goal=task.goal, risk_level=task.risk_level, status=AgentState.IDLE.value)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.post("/{task_id}/approve")
def approve_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    approved: bool = True,
    reason: str = "",
    db: Session = Depends(get_db)
):
    from datetime import datetime
    from app.models.domain import Task, Approval
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    approval = db.query(Approval).filter(Approval.task_id == task_id, Approval.status == "PENDING").first()
    if not approval:
        raise HTTPException(status_code=400, detail="No pending approval for this task")

    approval.status = "APPROVED" if approved else "REJECTED"
    approval.decision_at = datetime.utcnow()
    approval.decision_source = "USER"
    db.commit()

    # Resume the orchestrator in the background
    background_tasks.add_task(resume_agent_lifecycle, task_id, approved, reason)
    return {"status": "resumed", "approved": approved}

def resume_agent_lifecycle(task_id: str, approved: bool, reason: str):
    from app.db.session import SessionLocal
    from app.agent.goal_understanding import DeterministicGoalInterpreter
    from app.agent.planner import DeterministicPlanner
    from app.agent.policy import PolicyEngine
    from app.agent.actions.registry import action_registry
    from app.models.domain import Task, Plan
    from app.repositories.agent_repo import update_task_state, create_approval, save_plan, log_audit_event
    from datetime import datetime
    db = SessionLocal()
    try:
        class AgentRepository:
            def __init__(self, db_session):
                self.db = db_session
            def save_state_transition(self, transition, ctx):
                update_task_state(self.db, ctx.task_id, transition.to_state)
                if transition.to_state == AgentState.WAITING_APPROVAL:
                    create_approval(self.db, transition, ctx)
            def save_audit_event(self, event_type, status, metadata, ctx):
                log_audit_event(self.db, ctx.task_id, event_type, status, metadata)

        repo = AgentRepository(db)
        
        task = db.query(Task).filter(Task.id == task_id).first()
        plan_model = db.query(Plan).filter(Plan.task_id == task_id).first()
        
        context = ExecutionContext(task_id=task_id, plan_id=plan_model.id if plan_model else None)
        
        registry = action_registry
        policy = PolicyEngine()
        from app.agent.executor import ExecutionEngine
        from app.agent.verifier import DeterministicVerifier
        from app.agent.recovery import RecoveryEngine
        
        orchestrator = AgentOrchestrator(
            context=context,
            interpreter=DeterministicGoalInterpreter(),
            planner=DeterministicPlanner(),
            policy_engine=policy,
            execution_engine=ExecutionEngine(registry, policy),
            verifier=DeterministicVerifier(),
            recovery_engine=RecoveryEngine(),
            on_state_change=lambda t, c: repo.save_state_transition(t, c),
            on_audit_event=lambda e, s, m, c: repo.save_audit_event(e, s, m, c)
        )
        
        # We manually set state to WAITING_APPROVAL
        orchestrator.state_machine.current_state = AgentState.WAITING_APPROVAL
        
        # Rehydrate plan
        if plan_model:
            from app.agent.models import ExecutionPlan, PlanStep as AgentPlanStep, ActionDefinition
            steps = []
            for smodel in plan_model.steps:
                action = ActionDefinition(action_type=smodel.action_type, parameters=smodel.parameters, risk_level=smodel.risk_level)
                steps.append(AgentPlanStep(step_id=smodel.id, name=smodel.name, action=action, dependencies=smodel.dependencies))
            orchestrator.plan = ExecutionPlan(plan_id=plan_model.id, steps=steps)
            
        orchestrator.resume_from_approval(approved, reason)
    finally:
        db.close()

@router.get("/", response_model=List[TaskResponse])
def get_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = db.query(DBTask).offset(skip).limit(limit).all()
    return tasks

@router.post("/{task_id}/execute")
def execute_task(task_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = db.query(DBTask).filter(DBTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status not in [AgentState.IDLE.value, AgentState.FAILED.value, AgentState.CANCELLED.value]:
        raise HTTPException(status_code=400, detail="Task is already executing or completed")
        
    # Queue background task to not block API
    background_tasks.add_task(run_agent_lifecycle, task_id, task.goal, db)
    
    return {"message": "Execution started", "task_id": task_id}

@router.get("/{task_id}/audit")
def get_task_audit(task_id: str, db: Session = Depends(get_db)):
    events = get_audit_events(db, task_id)
    return [{"timestamp": e.timestamp, "type": e.event_type, "status": e.payload.get("status"), "payload": e.payload} for e in events]

@router.get("/{task_id}/timeline")
def get_task_timeline(task_id: str, db: Session = Depends(get_db)):
    task = db.query(DBTask).filter(DBTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task_id,
        "status": task.status,
        "created_at": task.created_at
    }
