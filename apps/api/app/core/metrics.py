from prometheus_client import Counter, Histogram, Gauge

# Tasks
TASKS_COMPLETED = Counter('linuxpilot_tasks_completed_total', 'Total tasks completed successfully')
TASKS_FAILED = Counter('linuxpilot_tasks_failed_total', 'Total tasks that failed')
TASK_DURATION = Histogram('linuxpilot_task_duration_seconds', 'Duration of completed tasks')

# Steps
STEP_LATENCY = Histogram('linuxpilot_step_latency_seconds', 'Latency of individual execution steps', ['action_type'])
STEP_VERIFICATION_FAILURES = Counter('linuxpilot_step_verification_failures_total', 'Number of step verification failures')
STEP_RETRIES = Counter('linuxpilot_step_retries_total', 'Number of times a step was retried')
STEP_REPLANS = Counter('linuxpilot_step_replans_total', 'Number of times a task was replanned')
STEP_ROLLBACKS = Counter('linuxpilot_step_rollbacks_total', 'Number of times a rollback was initiated')

# Safety & Policy
APPROVAL_WAITS = Counter('linuxpilot_approval_waits_total', 'Number of times an approval was requested')
SANDBOX_VIOLATIONS = Counter('linuxpilot_sandbox_violations_total', 'Number of sandbox violations blocked by policy')

# Active state
ACTIVE_TASKS = Gauge('linuxpilot_active_tasks', 'Currently active tasks', ['status'])
