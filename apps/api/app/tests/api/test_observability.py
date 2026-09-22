import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    content = response.text
    
    # Check that some of our custom metrics are present in the Prometheus output
    assert "linuxpilot_tasks_completed_total" in content
    assert "linuxpilot_tasks_failed_total" in content
    assert "linuxpilot_active_tasks" in content
    assert "linuxpilot_step_latency_seconds" in content
    assert "linuxpilot_sandbox_violations_total" in content

def test_structured_logger():
    from app.core.logging import log_event, structured_logger, CustomJsonFormatter
    import logging
    import io
    import json
    
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s'))
    structured_logger.addHandler(handler)
    
    log_event(
        event_type="TEST_EVENT",
        status="SUCCESS",
        component="test_runner",
        task_id="task_123",
        step_id="step_456",
        action="TEST_ACTION",
        latency_ms=42,
        payload={"secret": "my_password", "safe_data": "ok"}
    )
    
    structured_logger.removeHandler(handler)
    log_output = stream.getvalue()
    
    assert "TEST_EVENT" in log_output
    
    for line in log_output.splitlines():
        if "TEST_EVENT" in line:
            log_data = json.loads(line)
            assert log_data["event"] == "TEST_EVENT"
            assert log_data["status"] == "SUCCESS"
            assert log_data["component"] == "test_runner"
            assert log_data["task_id"] == "task_123"
            assert log_data["step_id"] == "step_456"
            assert log_data["action"] == "TEST_ACTION"
            assert log_data["latency_ms"] == 42
            
            assert "payload" in log_data
            assert log_data["payload"]["secret"] == "***REDACTED***"
            assert log_data["payload"]["safe_data"] == "ok"
