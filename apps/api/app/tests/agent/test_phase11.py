import pytest
from app.agent.actions.registry import ActionRegistry
from app.agent.models import ActionDefinition, SandboxConfig
from app.agent.actions.document_handlers import PDFExtractTextHandler, XLSXReadHandler, XLSXWriteHandler
from app.agent.actions.browser_handlers import BrowserSession, BrowserNavigateHandler, BrowserExtractHandler, BrowserFillHandler
from app.agent.orchestrator import AgentOrchestrator
from app.agent.context import ExecutionContext

import os

def test_context_passing_engine():
    # Test safe interpolation logic
    # We can invoke it by initializing orchestrator with mocks, or just calling _interpolate_parameters
    # We'll use a dummy orchestrator
    orchestrator = AgentOrchestrator(
        context=ExecutionContext(task_id="test"),
        interpreter=None, planner=None, policy_engine=None,
        execution_engine=None, verifier=None, recovery_engine=None
    )
    
    orchestrator.step_outputs = {
        "step_1": {"invoice_total": "$100.00"},
        "step_2": {"items": ["apple", "banana"]}
    }
    
    params = {
        "url": "https://example.com/submit",
        "form_data": {
            "total": "{{step_1.output.invoice_total}}",
            "missing": "{{step_3.output.missing}}",
            "first_item": "{{step_2.output.items.0}}"
        },
        "list_val": ["{{step_1.output.invoice_total}}"]
    }
    
    resolved = orchestrator._interpolate_parameters(params)
    
    assert resolved["form_data"]["total"] == "$100.00"
    assert resolved["form_data"]["first_item"] == "apple"
    assert resolved["form_data"]["missing"] == "{{step_3.output.missing}}" # Unresolved
    assert resolved["list_val"][0] == "$100.00"
    
def test_xlsx_read_write(tmp_path):
    file_path = str(tmp_path / "test.xlsx")
    
    # Temporarily allow tmp_path in document_handlers security_policy
    import app.agent.actions.document_handlers as dh
    dh.security_policy.allowed_roots.append(str(tmp_path.resolve()))
    
    write_handler = XLSXWriteHandler()
    read_handler = XLSXReadHandler()
    
    # Write
    action_write = ActionDefinition(
        action_type="document.xlsx.write",
        parameters={"path": file_path, "rows": [["Name", "Age"], ["Alice", 30], ["Bob", 25]]}
    )
    res_write = write_handler.execute(action_write)
    assert res_write.success
    assert res_write.output["rows_written"] == 3
    
    # Read
    action_read = ActionDefinition(
        action_type="document.xlsx.read",
        parameters={"path": file_path}
    )
    res_read = read_handler.execute(action_read)
    assert res_read.success
    assert res_read.output["rows"][1][0] == "Alice"
    assert res_read.output["rows"][2][1] == 25

def test_browser_handlers():
    # Because this is a headless browser, it should run fine in tests
    nav_handler = BrowserNavigateHandler()
    ext_handler = BrowserExtractHandler()
    
    action_nav = ActionDefinition(
        action_type="browser.navigate",
        parameters={"url": "data:text/html,<html><body><h1 id='hdr'>Hello Playwright</h1></body></html>"}
    )
    res_nav = nav_handler.execute(action_nav)
    assert res_nav.success
    
    action_ext = ActionDefinition(
        action_type="browser.extract",
        parameters={"selector": "#hdr"}
    )
    res_ext = ext_handler.execute(action_ext)
    assert res_ext.success
    assert res_ext.output["texts"] == ["Hello Playwright"]
    
    # Clean up browser session
    BrowserSession.get_instance().close()

def test_policy_engine_phase11_rules():
    from app.agent.policy import PolicyEngine, RiskLevel, PolicyDecisionResult
    policy = PolicyEngine()
    
    # Browser read should be allowed
    decision1 = policy.evaluate(ActionDefinition(action_type="browser.navigate", parameters={}))
    assert decision1.risk_level == RiskLevel.LEVEL_1_NON_DESTRUCTIVE
    assert decision1.decision == PolicyDecisionResult.ALLOW
    
    # Browser submit should require approval
    decision2 = policy.evaluate(ActionDefinition(action_type="browser.submit", parameters={}))
    assert decision2.risk_level == RiskLevel.LEVEL_2_MODIFY
    assert decision2.decision == PolicyDecisionResult.REQUIRE_APPROVAL
    
    # XLSX write should require approval
    decision3 = policy.evaluate(ActionDefinition(action_type="document.xlsx.write", parameters={}))
    assert decision3.risk_level == RiskLevel.LEVEL_2_MODIFY
    assert decision3.decision == PolicyDecisionResult.REQUIRE_APPROVAL
