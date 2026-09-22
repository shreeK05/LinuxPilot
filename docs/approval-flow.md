# Approval Flow

## Lifecycle
1. The `PolicyEngine` evaluates the Plan and identifies high-risk actions.
2. If `REQUIRE_APPROVAL` is flagged, `AgentOrchestrator` transitions the task to `WAITING_APPROVAL`.
3. An `Approval` record is inserted into the PostgreSQL database.
4. The orchestration loop exits (pauses).
5. The User views the React Frontend `ApprovalCenter` and submits an approval decision.
6. The `POST /api/v1/tasks/{task_id}/approve` endpoint transitions the Approval record and calls `resume_agent_lifecycle` in the background.
7. The Orchestrator rehydrates and proceeds to `READY` / `EXECUTING`.
