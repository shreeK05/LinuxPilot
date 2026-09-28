from typing import Any
from app.agent.actions.registry import ActionHandler, ActionExecutionResult
from app.agent.models import ActionDefinition

import threading

class BrowserSession:
    _local = threading.local()
    
    @classmethod
    def get_instance(cls):
        if not hasattr(cls._local, "instance"):
            cls._local.instance = cls()
        return cls._local.instance

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def get_page(self):
        if self.page is None:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
        return self.page

    def close(self):
        if self.page:
            self.page.close()
            self.page = None
        if self.context:
            self.context.close()
            self.context = None
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
        if hasattr(BrowserSession._local, "instance"):
            del BrowserSession._local.instance

class BrowserNavigateHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            url = action.parameters.get("url")
            if not url:
                return ActionExecutionResult(success=False, output=None, error="URL is required")
                
            if url.lower().startswith("file://"):
                return ActionExecutionResult(success=False, output=None, error="Local file URLs are not permitted in the browser handler. Use filesystem actions instead.")
            
            page = BrowserSession.get_instance().get_page()
            page.goto(url, wait_until="domcontentloaded")
            return ActionExecutionResult(success=True, output={"url": page.url, "title": page.title()})
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=f"Failed to navigate: {str(e)}")

class BrowserExtractHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            selector = action.parameters.get("selector")
            page = BrowserSession.get_instance().get_page()
            
            if selector:
                elements = page.query_selector_all(selector)
                texts = [el.inner_text() for el in elements]
                return ActionExecutionResult(success=True, output={"text": "\n\n".join(texts)})
            else:
                # Full page text
                text = page.locator("body").inner_text()
                return ActionExecutionResult(success=True, output={"text": text})
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=f"Failed to extract: {str(e)}")

class BrowserFillHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            selector = action.parameters.get("selector")
            value = action.parameters.get("value")
            if not selector or value is None:
                return ActionExecutionResult(success=False, output=None, error="Selector and value are required")
                
            page = BrowserSession.get_instance().get_page()
            page.fill(selector, str(value))
            return ActionExecutionResult(success=True, output={"selector": selector, "filled": True})
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=f"Failed to fill form: {str(e)}")

class BrowserClickHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            selector = action.parameters.get("selector")
            if not selector:
                return ActionExecutionResult(success=False, output=None, error="Selector is required")
                
            page = BrowserSession.get_instance().get_page()
            page.click(selector)
            return ActionExecutionResult(success=True, output={"selector": selector, "clicked": True})
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=f"Failed to click: {str(e)}")

class BrowserSubmitHandler(ActionHandler):
    def execute(self, action: ActionDefinition) -> ActionExecutionResult:
        try:
            selector = action.parameters.get("selector")
            if not selector:
                return ActionExecutionResult(success=False, output=None, error="Selector is required")
                
            page = BrowserSession.get_instance().get_page()
            
            # Wait for navigation after submit
            with page.expect_navigation():
                page.click(selector)
                
            return ActionExecutionResult(success=True, output={"url": page.url, "submitted": True})
        except Exception as e:
            return ActionExecutionResult(success=False, output=None, error=f"Failed to submit: {str(e)}")
