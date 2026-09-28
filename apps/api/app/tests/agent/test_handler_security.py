import pytest
import os
from pathlib import Path

# Import registry first to resolve circular dependencies
import app.agent.actions.registry
from app.agent.actions.document_handlers import PDFExtractTextHandler, XLSXWriteHandler
from app.agent.models import ActionDefinition
from app.adapters.linux.filesystem.security import FilesystemSecurityError

def test_pdf_handler_security_violation():
    handler = PDFExtractTextHandler()
    action = ActionDefinition(
        action_type="document.pdf.extract_text",
        parameters={"path": "/etc/passwd"},
        timeout_seconds=5
    )
    # The handler catches the exception and returns ActionExecutionResult with error string
    result = handler.execute(action)
    assert result.success is False
    assert "protected system directory" in result.error or "outside allowed roots" in result.error

def test_xlsx_write_security_violation():
    handler = XLSXWriteHandler()
    action = ActionDefinition(
        action_type="document.xlsx.write",
        parameters={"path": "/etc/passwd", "rows": [["test"]]},
        timeout_seconds=5
    )
    result = handler.execute(action)
    assert result.success is False
    assert "protected system directory" in result.error or "outside allowed roots" in result.error

def test_browser_file_url_blocked():
    from app.agent.actions.browser_handlers import BrowserNavigateHandler
    handler = BrowserNavigateHandler()
    action = ActionDefinition(
        action_type="browser.navigate",
        parameters={"url": "file:///etc/passwd"},
        timeout_seconds=5
    )
    result = handler.execute(action)
    assert result.success is False
    assert "Local file URLs are not permitted" in result.error
