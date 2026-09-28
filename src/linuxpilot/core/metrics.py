"""
Metrics and observability
"""

from prometheus_client import Counter, Histogram, Gauge

# Task metrics
tasks_total = Counter(
    "lp_tasks_total",
    "Total number of tasks",
    ["status"]
)

steps_total = Counter(
    "lp_steps_total",
    "Total number of steps executed",
    ["tool", "result"]
)

rollbacks_total = Counter(
    "lp_rollbacks_total",
    "Total number of rollbacks",
    ["reason"]
)

invariant_violations_total = Counter(
    "lp_invariant_violations_total",
    "Total number of invariant violations",
    ["invariant_id"]
)

seccomp_violations_total = Counter(
    "lp_seccomp_violations_total",
    "Total number of seccomp violations",
)

# Latency metrics
step_duration_seconds = Histogram(
    "lp_step_duration_seconds",
    "Step execution duration in seconds",
    ["tool"]
)

llm_latency_seconds = Histogram(
    "lp_llm_latency_seconds",
    "LLM request latency in seconds",
    ["provider"]
)

# Resource metrics
upper_bytes = Gauge(
    "lp_upper_bytes",
    "Size of upper layer in bytes",
    ["task_id"]
)

# LLM metrics
llm_tokens_total = Counter(
    "lp_llm_tokens_total",
    "Total LLM tokens used",
    ["provider"]
)

# Export all metrics
metrics = {
    "tasks_total": tasks_total,
    "steps_total": steps_total,
    "rollbacks_total": rollbacks_total,
    "invariant_violations_total": invariant_violations_total,
    "seccomp_violations_total": seccomp_violations_total,
    "step_duration_seconds": step_duration_seconds,
    "llm_latency_seconds": llm_latency_seconds,
    "upper_bytes": upper_bytes,
    "llm_tokens_total": llm_tokens_total,
}
