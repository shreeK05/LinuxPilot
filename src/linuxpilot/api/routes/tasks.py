"""
Task management endpoints
Full REST API for task lifecycle with diff, rollback, audit, and kill
"""

import asyncio
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from linuxpilot.models import ExecutionContext, Risk
from linuxpilot.orchestrator.orchestrator import TaskOrchestrator
from linuxpilot.planning.planner import LLMPlanner
from linuxpilot.planning.policy import PolicyEngine
from linuxpilot.llm.gateway import LLMGateway
from linuxpilot.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Active task storage (in production, consider a persistence layer)
active_tasks: dict[str, TaskOrchestrator] = {}


# ── Request/Response Models ──────────────────────────────────

class TaskCreateRequest(BaseModel):
    goal: str
    mode: str = Field(default="hybrid", pattern="^(api|gui|hybrid)$")
    allowed_roots: list[str] = Field(default=["~/Downloads", "~/Documents"])
    auto_approve: bool = False


class TaskResponse(BaseModel):
    task_id: str
    goal: str
    status: str
    mode: str = "hybrid"
    current_step: int = 0
    total_steps: int = 0
    step_count: int = 0
    rollback_count: int = 0
    elapsed_time: float = 0.0


class ApprovalRequest(BaseModel):
    approved: bool
    step_id: Optional[str] = None
    reason: Optional[str] = None


class RollbackRequest(BaseModel):
    to_step: str


class DiffEntry(BaseModel):
    kind: str
    path: str
    description: str


class DiffResponse(BaseModel):
    task_id: str
    changes: list[DiffEntry]
    summary: dict[str, int]


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int


# ── Helper ───────────────────────────────────────────────────

def _get_orchestrator(task_id: str) -> TaskOrchestrator:
    """Get orchestrator or raise 404"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return active_tasks[task_id]


def _task_response(task_id: str, orch: TaskOrchestrator) -> TaskResponse:
    """Build a TaskResponse from orchestrator state"""
    status = orch.get_status()
    return TaskResponse(
        task_id=task_id,
        goal=orch.goal,
        status=status["state"],
        mode=getattr(orch, "mode", "hybrid"),
        current_step=status["current_step"],
        total_steps=status["total_steps"],
        step_count=status["step_count"],
        rollback_count=status["rollback_count"],
        elapsed_time=status["elapsed_time"],
    )


async def _emit_ws_event(task_id: str, event: dict):
    """Emit an event to WebSocket listeners"""
    try:
        from linuxpilot.api.routes.websocket import get_connection_manager
        mgr = get_connection_manager()
        await mgr.broadcast(task_id, event)
    except Exception:
        pass  # WebSocket errors should not crash the task


def _on_state_change(transition, context):
    """Callback for orchestrator state changes — fires WebSocket events"""
    try:
        event = {
            "type": "state_change",
            "from_state": transition.from_state.value,
            "to_state": transition.to_state.value,
            "reason": transition.reason,
            "timestamp": transition.timestamp,
        }
        asyncio.get_event_loop().create_task(
            _emit_ws_event(context.task_id, event)
        )
    except RuntimeError:
        pass  # No event loop available (sync context)


def _on_audit_event(kind, status, payload, context):
    """Callback for audit events — fires WebSocket events"""
    try:
        event = {
            "type": "audit_event",
            "kind": kind,
            "status": status,
            "payload": payload,
        }
        asyncio.get_event_loop().create_task(
            _emit_ws_event(context.task_id, event)
        )
    except RuntimeError:
        pass


# ── Endpoints ────────────────────────────────────────────────

@router.get("/", response_model=TaskListResponse)
async def list_tasks():
    """List all active tasks"""
    tasks = [_task_response(tid, orch) for tid, orch in active_tasks.items()]
    return TaskListResponse(tasks=tasks, total=len(tasks))


@router.post("/", response_model=TaskResponse)
async def create_task(request: TaskCreateRequest, background_tasks: BackgroundTasks):
    """Create and start a new task"""
    task_id = f"t-{uuid.uuid4().hex[:8]}"

    context = ExecutionContext(
        task_id=task_id,
        allowed_roots=request.allowed_roots,
    )

    # Initialize components
    try:
        llm_gateway = LLMGateway()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"No LLM providers available: {e}")

    planner = LLMPlanner(llm_gateway)
    policy_engine = PolicyEngine()

    orchestrator = TaskOrchestrator(
        task_id=task_id,
        goal=request.goal,
        context=context,
        llm_gateway=llm_gateway,
        planner=planner,
        policy_engine=policy_engine,
        on_state_change=_on_state_change,
        on_audit_event=_on_audit_event,
    )
    orchestrator.mode = request.mode

    active_tasks[task_id] = orchestrator

    # Run the task in the background
    def run_task():
        try:
            orchestrator.start()
            if request.auto_approve and orchestrator.fsm.current_state.value == "waiting_approval":
                orchestrator.resume_with_approval(True)
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")

    background_tasks.add_task(run_task)

    return _task_response(task_id, orchestrator)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get task status"""
    orch = _get_orchestrator(task_id)
    return _task_response(task_id, orch)


@router.post("/{task_id}/approve")
async def approve_task(task_id: str, request: ApprovalRequest):
    """Approve or reject a task/step waiting for approval"""
    orch = _get_orchestrator(task_id)

    if orch.fsm.current_state.value != "waiting_approval":
        raise HTTPException(status_code=400, detail="Task is not waiting for approval")

    success = orch.resume_with_approval(request.approved)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to process approval")

    return {"status": "ok", "approved": request.approved}


@router.get("/{task_id}/diff", response_model=DiffResponse)
async def get_task_diff(task_id: str):
    """Get the diff of changes made by the task (git diff for your desktop)"""
    orch = _get_orchestrator(task_id)

    if not orch.workspace_info:
        raise HTTPException(status_code=400, detail="No workspace available")

    try:
        from linuxpilot.workspace.diff import DiffAnalyzer
        analyzer = DiffAnalyzer(orch.workspace_info)
        changes = analyzer.analyze()
        summary = analyzer.get_summary(changes)

        return DiffResponse(
            task_id=task_id,
            changes=[DiffEntry(**c) for c in changes],
            summary=summary,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diff analysis failed: {e}")


@router.post("/{task_id}/commit")
async def commit_task(task_id: str):
    """Commit changes from a completed task to real data"""
    orch = _get_orchestrator(task_id)

    if orch.fsm.current_state.value != "review":
        raise HTTPException(
            status_code=400,
            detail=f"Task is in state '{orch.fsm.current_state.value}', not 'review'"
        )

    success = orch.commit_changes()
    if not success:
        raise HTTPException(status_code=500, detail="Commit failed")

    return {"status": "committed", "task_id": task_id}


@router.post("/{task_id}/discard")
async def discard_task(task_id: str):
    """Discard all changes — real data untouched"""
    orch = _get_orchestrator(task_id)

    success = orch.discard_changes()
    if not success:
        raise HTTPException(status_code=500, detail="Discard failed")

    del active_tasks[task_id]
    return {"status": "discarded", "task_id": task_id}


@router.post("/{task_id}/rollback")
async def rollback_task(task_id: str, request: RollbackRequest):
    """Manually rollback to a specific checkpoint"""
    orch = _get_orchestrator(task_id)

    if not orch.checkpoint_mgr:
        raise HTTPException(status_code=400, detail="No checkpoint manager available")

    checkpoints = orch.checkpoint_mgr.list_checkpoints()
    if request.to_step not in checkpoints:
        raise HTTPException(
            status_code=400,
            detail=f"Checkpoint '{request.to_step}' not found. Available: {checkpoints}"
        )

    success = orch.checkpoint_mgr.restore_checkpoint(request.to_step)
    if not success:
        raise HTTPException(status_code=500, detail="Rollback failed")

    return {"status": "rolled_back", "to_step": request.to_step}


@router.post("/{task_id}/kill")
async def kill_task(task_id: str):
    """Emergency kill switch — kills all processes and discards changes"""
    orch = _get_orchestrator(task_id)

    try:
        orch.discard_changes()
    except Exception as e:
        logger.error(f"Kill cleanup failed: {e}")

    if task_id in active_tasks:
        del active_tasks[task_id]

    return {"status": "killed", "task_id": task_id}


@router.get("/{task_id}/audit")
async def get_task_audit(task_id: str, kind: Optional[str] = None):
    """Get audit log entries for a task"""
    orch = _get_orchestrator(task_id)

    entries = orch.audit_chain.get_entries(kind_filter=kind)
    is_valid, error = orch.audit_chain.verify()

    return {
        "task_id": task_id,
        "entries": [e.model_dump() for e in entries],
        "chain_verified": is_valid,
        "verification_error": error,
        "final_hash": orch.audit_chain.get_final_hash(),
    }


@router.get("/{task_id}/checkpoints")
async def get_task_checkpoints(task_id: str):
    """List available checkpoints for a task"""
    orch = _get_orchestrator(task_id)

    if not orch.checkpoint_mgr:
        return {"task_id": task_id, "checkpoints": []}

    checkpoints = orch.checkpoint_mgr.list_checkpoints()
    return {"task_id": task_id, "checkpoints": checkpoints}
