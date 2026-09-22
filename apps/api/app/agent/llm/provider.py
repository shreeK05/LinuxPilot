import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel
from openai import OpenAI, AsyncOpenAI

T = TypeVar("T", bound=BaseModel)

class LLMProviderError(Exception):
    pass

class LLMProvider(ABC):
    """
    Abstract interface for LLM providers.
    """
    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: Type[T],
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> T:
        """Generates a structured Pydantic response."""
        pass
        
    @abstractmethod
    def get_audit_metadata(self) -> Dict[str, Any]:
        pass

class OpenAICompatibleProvider(LLMProvider):
    """
    Provider that uses the official OpenAI Python SDK.
    Compatible with OpenAI, Groq, Ollama, and any other OpenAI-compatible API.
    """
    def __init__(
        self, 
        base_url: Optional[str] = None, 
        api_key: Optional[str] = None, 
        model: Optional[str] = None,
        timeout: int = 60
    ):
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "dummy_key")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        
        # Use httpx client if needed for timeout
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=timeout
        )
        
        self.last_metadata = {}

    def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: Type[T],
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> T:
        try:
            # We use the beta parse feature of the openai SDK to enforce structured output
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format=response_model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Save metadata
            self.last_metadata = {
                "provider": "openai_compatible",
                "model": self.model,
                "request_id": response.id,
                "usage": dict(response.usage) if response.usage else None
            }
            
            if response.choices[0].message.refusal:
                raise LLMProviderError(f"Model refused: {response.choices[0].message.refusal}")
                
            return response.choices[0].message.parsed
            
        except Exception as e:
            self.last_metadata = {
                "provider": "openai_compatible",
                "model": self.model,
                "error": str(e)
            }
            raise LLMProviderError(f"Failed to generate structured response: {str(e)}")

    def get_audit_metadata(self) -> Dict[str, Any]:
        return self.last_metadata


class MockProvider(LLMProvider):
    """
    Mock provider for testing without an API key or active model.
    """
    def __init__(self, mock_responses: Dict[str, Any] = None):
        self.mock_responses = mock_responses or {}
        self.last_metadata = {}

    def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: Type[T],
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> T:
        
        self.last_metadata = {
            "provider": "mock",
            "model": "mock-model",
            "usage": {"total_tokens": 42}
        }
        
        # If a specific mock is set for this type
        if response_model.__name__ in self.mock_responses:
            return response_model.model_validate(self.mock_responses[response_model.__name__])
            
        # Fallback to raising error if not mocked
        raise LLMProviderError(f"No mock response configured for {response_model.__name__}")

    def get_audit_metadata(self) -> Dict[str, Any]:
        return self.last_metadata

def get_llm_provider() -> LLMProvider:
    """Factory to get the provider based on environment."""
    provider_name = os.getenv("LLM_PROVIDER", "mock").lower()
    
    if provider_name == "mock":
        return MockProvider()
    elif provider_name in ["openai", "groq", "ollama"]:
        return OpenAICompatibleProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
