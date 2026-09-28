"""
WebSocket endpoint for live task events
Streams step/verify/rollback events to the dashboard in real-time
"""

import asyncio
import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections for task event streaming"""

    def __init__(self):
        # task_id -> list of connected websockets
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)
        logger.info(f"WebSocket connected for task {task_id}")

    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            self.active_connections[task_id] = [
                ws for ws in self.active_connections[task_id] if ws != websocket
            ]
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        logger.info(f"WebSocket disconnected for task {task_id}")

    async def broadcast(self, task_id: str, event: dict):
        """Send event to all connections watching this task"""
        if task_id not in self.active_connections:
            return

        message = json.dumps(event, default=str)
        disconnected = []

        for ws in self.active_connections[task_id]:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected
        for ws in disconnected:
            self.disconnect(ws, task_id)

    async def broadcast_all(self, event: dict):
        """Send event to all connections"""
        message = json.dumps(event, default=str)
        for task_id in list(self.active_connections.keys()):
            for ws in self.active_connections.get(task_id, []):
                try:
                    await ws.send_text(message)
                except Exception:
                    pass


# Singleton connection manager
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager"""
    return manager


@router.websocket("/tasks/{task_id}/events")
async def task_events(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for live task events.

    Events sent:
    - state_change: {type, from_state, to_state, reason, timestamp}
    - step_started: {type, step_id, intent, tool}
    - step_completed: {type, step_id, duration_ms}
    - verification: {type, step_id, success, error}
    - invariant_check: {type, success, error}
    - rollback: {type, from_step, to_step}
    - audit_event: {type, kind, payload}
    - plan_created: {type, steps_count, steps}
    - task_completed: {type, status, final_state}
    """
    await manager.connect(websocket, task_id)

    try:
        # Send initial state
        from linuxpilot.api.routes.tasks import active_tasks

        if task_id in active_tasks:
            orchestrator = active_tasks[task_id]
            await websocket.send_json({
                "type": "initial_state",
                "task_id": task_id,
                "state": orchestrator.fsm.current_state.value,
                "goal": orchestrator.goal,
                "current_step": orchestrator.current_step_index,
                "total_steps": len(orchestrator.plan.steps) if orchestrator.plan else 0,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"Task {task_id} not found",
            })

        # Keep connection alive and listen for client messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
    finally:
        manager.disconnect(websocket, task_id)
