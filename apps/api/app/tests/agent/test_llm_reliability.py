import pytest
import openai
from unittest.mock import MagicMock, patch
from pydantic import BaseModel
from typing import List

from app.agent.llm.provider import OpenAICompatibleProvider, LLMProviderError
from app.agent.planner import LLMPlanner, PlannerError
from app.agent.verifier import LLMSemanticVerifier
from app.agent.models import GoalUnderstanding, PlanStep, ActionDefinition

class DummyResponseModel(BaseModel):
    message: str

class MockMessage:
    def __init__(self, parsed=None, refusal=None):
        self.parsed = parsed
        self.refusal = refusal

class MockChoice:
    def __init__(self, message):
        self.message = message

class MockResponse:
    def __init__(self, parsed=None, refusal=None, id="req_123"):
        self.choices = [MockChoice(MockMessage(parsed=parsed, refusal=refusal))]
        self.id = id
        self.usage = {"total_tokens": 10}

@pytest.fixture
def mock_client():
    client = MagicMock()
    return client

@pytest.fixture
def provider(mock_client):
    provider = OpenAICompatibleProvider()
    provider.client = mock_client
    return provider

def test_successful_first_request(provider, mock_client):
    # A. Successful first LLM request
    mock_client.beta.chat.completions.parse.return_value = MockResponse(
        parsed=DummyResponseModel(message="success")
    )
    
    res = provider.generate_structured("prompt", "system", DummyResponseModel)
    assert res.message == "success"
    assert mock_client.beta.chat.completions.parse.call_count == 1

def test_retry_on_rate_limit(provider, mock_client):
    # B. Retry after a simulated rate-limit error
    mock_client.beta.chat.completions.parse.side_effect = [
        openai.RateLimitError("Rate limit", response=MagicMock(), body=None),
        MockResponse(parsed=DummyResponseModel(message="success_after_retry"))
    ]
    
    res = provider.generate_structured("prompt", "system", DummyResponseModel)
    assert res.message == "success_after_retry"
    assert mock_client.beta.chat.completions.parse.call_count == 2

def test_retry_on_timeout(provider, mock_client):
    # C. Retry after a simulated timeout
    mock_client.beta.chat.completions.parse.side_effect = [
        openai.APITimeoutError(request=MagicMock()),
        MockResponse(parsed=DummyResponseModel(message="success_after_timeout"))
    ]
    
    res = provider.generate_structured("prompt", "system", DummyResponseModel)
    assert res.message == "success_after_timeout"
    assert mock_client.beta.chat.completions.parse.call_count == 2

def test_retry_stops_after_max_attempts(provider, mock_client):
    # D. Retry stops after the configured maximum attempts (3)
    mock_client.beta.chat.completions.parse.side_effect = [
        openai.RateLimitError("Rate limit 1", response=MagicMock(), body=None),
        openai.RateLimitError("Rate limit 2", response=MagicMock(), body=None),
        openai.RateLimitError("Rate limit 3", response=MagicMock(), body=None),
        openai.RateLimitError("Rate limit 4", response=MagicMock(), body=None),
    ]
    
    with pytest.raises(openai.RateLimitError):
        provider.generate_structured("prompt", "system", DummyResponseModel)
        
    assert mock_client.beta.chat.completions.parse.call_count == 3

def test_permanent_errors_not_retried(provider, mock_client):
    # E. Permanent/non-retryable errors are not endlessly retried
    mock_client.beta.chat.completions.parse.side_effect = openai.AuthenticationError("Bad auth", response=MagicMock(), body=None)
    
    with pytest.raises(LLMProviderError):
        provider.generate_structured("prompt", "system", DummyResponseModel)
        
    assert mock_client.beta.chat.completions.parse.call_count == 1

def test_replan_context_truncation():
    # G. 1,000,000-character error/replan context is safely truncated
    # H. Truncation marker is present
    registry = MagicMock()
    registry._handlers = {"test.action": None}
    
    provider = MagicMock()
    planner = LLMPlanner(provider=provider, registry=registry)
    
    long_error = "A" * 1000000
    
    # We mock generate_structured to capture the prompt sent
    def mock_generate(*args, **kwargs):
        prompt = kwargs.get('prompt')
        assert len(prompt) < 1000000
        assert "...[TRUNCATED]" in prompt
        # Return empty list to fail parsing gracefully in the test or just fake response
        mock_resp = MagicMock()
        mock_resp.steps = []
        return mock_resp
        
    provider.generate_structured.side_effect = mock_generate
    
    goal = GoalUnderstanding(intent="test", objective="test", entities=[], constraints=[], preconditions=[], expected_outcome="", risk_assessment="", required_permissions=[], relevant_context="")
    plan = MagicMock()
    plan.steps = []
    failed_step = PlanStep(step_id="1", name="step", dependencies=[], action=ActionDefinition(action_type="test", parameters={}))
    
    planner.replan(goal, plan, failed_step, long_error, [])
    assert provider.generate_structured.call_count == 1

def test_output_context_truncation():
    # F. 1,000,000-character execution output is safely truncated
    # H. Truncation marker is present
    provider = MagicMock()
    verifier = LLMSemanticVerifier(provider=provider)
    
    long_output = "B" * 1000000
    
    def mock_generate(*args, **kwargs):
        prompt = kwargs.get('prompt')
        assert len(prompt) < 1000000
        assert "...[TRUNCATED]" in prompt
        mock_resp = MagicMock()
        mock_resp.success = True
        return mock_resp
        
    provider.generate_structured.side_effect = mock_generate
    
    action = ActionDefinition(action_type="test", parameters={}, expected_result="success")
    verifier.verify(action, long_output)
    
    assert provider.generate_structured.call_count == 1

def test_normal_short_output_unchanged():
    # I. Normal short output remains unchanged
    provider = MagicMock()
    verifier = LLMSemanticVerifier(provider=provider)
    
    short_output = "Short output"
    
    def mock_generate(*args, **kwargs):
        prompt = kwargs.get('prompt')
        assert "...[TRUNCATED]" not in prompt
        assert "Short output" in prompt
        mock_resp = MagicMock()
        mock_resp.success = True
        return mock_resp
        
    provider.generate_structured.side_effect = mock_generate
    
    action = ActionDefinition(action_type="test", parameters={}, expected_result="success")
    verifier.verify(action, short_output)
    
    assert provider.generate_structured.call_count == 1

def test_existing_structured_plan_generation(provider, mock_client):
    # J. Existing structured plan generation still works
    registry = MagicMock()
    registry._handlers = {"test.action": None}
    planner = LLMPlanner(provider=provider, registry=registry)
    
    class MockParams(BaseModel):
        def model_dump(self, **kwargs):
            return {}

    class MockActionDef(BaseModel):
        action_type: str = "test.action"
        parameters: MockParams = MockParams()
        expected_result: str = None
        verification_requirements: MockParams = None
        
    class MockStep(BaseModel):
        step_id: str = "1"
        name: str = "Test"
        dependencies: list = []
        action: MockActionDef = MockActionDef()
        
    class MockPlan(BaseModel):
        steps: list = [MockStep()]
        
    mock_client.beta.chat.completions.parse.return_value = MockResponse(
        parsed=MockPlan()
    )
    
    goal = GoalUnderstanding(intent="test", objective="test", entities=[], constraints=[], preconditions=[], expected_outcome="", risk_assessment="", required_permissions=[], relevant_context="")
    
    plan = planner.create_plan(goal)
    assert len(plan.steps) == 1
    assert plan.steps[0].action.action_type == "test.action"
