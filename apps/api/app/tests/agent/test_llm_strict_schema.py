import pytest
from pydantic import ValidationError
from app.agent.planner import LLMActionDef, LLMActionParameters
from app.agent.models import ActionDefinition

def test_llm_action_def_strict_schema():
    """Prove that LLMActionDef uses strict schema compliant dicts"""
    schema = LLMActionDef.model_json_schema()
    
    # Check that parameters is an object and strictly sets additionalProperties: False
    params_schema = schema['$defs']['LLMActionParameters']
    assert params_schema.get('additionalProperties') is False
    
    # Check that it allows typical action parameters
    assert 'command' in params_schema['properties']
    assert 'path' in params_schema['properties']
    assert 'source' in params_schema['properties']

def test_action_definition_preserves_dict():
    """Prove that we didn't break Python logic for parameters.get()"""
    action = ActionDefinition(
        action_type="test",
        parameters={"path": "/tmp", "command": "ls"}
    )
    # The application code does this everywhere:
    assert action.parameters.get("path") == "/tmp"
    assert action.parameters.get("command") == "ls"
    assert action.parameters.get("unknown_param") is None

def test_llm_action_def_conversion_to_action_def():
    """Prove that strict LLM output successfully maps to dynamic ActionDefinition"""
    llm_action = LLMActionDef(
        action_type="filesystem.read",
        parameters=LLMActionParameters(path="/etc/passwd")
    )
    
    # Simulate planner mapping
    domain_action = ActionDefinition(
        action_type=llm_action.action_type,
        parameters=llm_action.parameters.model_dump(exclude_none=True),
        expected_result=llm_action.expected_result,
        verification_requirements=llm_action.verification_requirements.model_dump(exclude_none=True) if llm_action.verification_requirements else None
    )
    
    assert domain_action.action_type == "filesystem.read"
    assert domain_action.parameters.get("path") == "/etc/passwd"
    # Ensure empty fields are not serialized into the dict unnecessarily
    assert "command" not in domain_action.parameters

def test_invalid_parameters_rejected_by_strict_schema():
    """Prove that invalid parameters would be rejected by the schema validation"""
    with pytest.raises(ValidationError):
        LLMActionParameters(unknown_key="value")
