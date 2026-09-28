import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel
import openai
from openai import OpenAI, AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.APIConnectionError,
            openai.InternalServerError
        )),
        reraise=True
    )
    def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: Type[T],
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> T:
        try:
            # We use standard json_object for Groq compatibility
            # Instruct the model to return JSON matching the schema
            schema = response_model.model_json_schema()
            sys_prompt = system_prompt + f"\n\nYou MUST return ONLY valid JSON matching this schema: {schema}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
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
            
            content = response.choices[0].message.content
            return response_model.model_validate_json(content)
            
        except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError, openai.InternalServerError) as e:
            # Let tenacity handle these
            self.last_metadata = {
                "provider": "openai_compatible",
                "model": self.model,
                "error": str(e)
            }
            raise e
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
