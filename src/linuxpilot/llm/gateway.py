"""
LLM Gateway with provider fallback and cassette support
"""

import hashlib
import json
from typing import Optional, Any, Type
from pathlib import Path
from abc import ABC, abstractmethod
import time
import logging

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel

from linuxpilot.config import settings
from linuxpilot.llm.cassette import CassetteManager

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def complete(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> str:
        """Generate text completion"""
        pass
    
    @abstractmethod
    def complete_structured(
        self,
        messages: list[ChatCompletionMessageParam],
        response_model: Type[BaseModel],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> BaseModel:
        """Generate structured completion with schema validation"""
        pass


class OllamaProvider(LLMProvider):
    """Ollama provider for local models"""
    
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.client = OpenAI(
            base_url=f"{self.base_url}/v1",
            api_key="ollama",  # Ollama doesn't require a real key
        )
    
    def complete(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            raise
    
    def complete_structured(
        self,
        messages: list[ChatCompletionMessageParam],
        response_model: Type[BaseModel],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> BaseModel:
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response.parsed
        except Exception as e:
            logger.error(f"Ollama structured completion failed: {e}")
            raise


class GroqProvider(LLMProvider):
    """Groq provider for fast cloud inference"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        
        if not self.api_key:
            raise ValueError("Groq API key is required")
        
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=self.api_key,
        )
    
    def complete(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq completion failed: {e}")
            raise
    
    def complete_structured(
        self,
        messages: list[ChatCompletionMessageParam],
        response_model: Type[BaseModel],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> BaseModel:
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response.parsed
        except Exception as e:
            logger.error(f"Groq structured completion failed: {e}")
            raise


class GeminiProvider(LLMProvider):
    """Google Gemini provider"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        
        if not self.api_key:
            raise ValueError("Gemini API key is required")
        
        # Gemini uses a different API structure, so we'll use the OpenAI-compatible endpoint
        self.client = OpenAI(
            base_url=f"https://generativelanguage.googleapis.com/v1beta/{self.model}",
            api_key=self.api_key,
        )
    
    def complete(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Gemini completion failed: {e}")
            raise
    
    def complete_structured(
        self,
        messages: list[ChatCompletionMessageParam],
        response_model: Type[BaseModel],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> BaseModel:
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response.parsed
        except Exception as e:
            logger.error(f"Gemini structured completion failed: {e}")
            raise


class LLMGateway:
    """
    Gateway for LLM providers with automatic fallback and cassette support
    """
    
    def __init__(self):
        self.providers: dict[str, LLMProvider] = {}
        self.provider_order = settings.LLM_PROVIDER_ORDER
        self.cassette = CassetteManager(settings.CASSETTE_DIR, settings.CASSETTE_MODE)
        
        # Initialize available providers
        self._init_providers()
    
    def _init_providers(self):
        """Initialize providers based on configuration"""
        try:
            self.providers["ollama"] = OllamaProvider()
            logger.info("Ollama provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama: {e}")
        
        if settings.GROQ_API_KEY:
            try:
                self.providers["groq"] = GroqProvider()
                logger.info("Groq provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq: {e}")
        
        if settings.GEMINI_API_KEY:
            try:
                self.providers["gemini"] = GeminiProvider()
                logger.info("Gemini provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")
        
        if not self.providers:
            raise RuntimeError("No LLM providers available")
    
    def _get_cassette_key(
        self,
        messages: list[ChatCompletionMessageParam],
        model: str,
        temperature: float,
    ) -> str:
        """Generate a unique key for cassette recording"""
        key_data = {
            "model": model,
            "temperature": temperature,
            "messages": messages,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def complete(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
        preferred_provider: Optional[str] = None,
    ) -> str:
        """
        Generate text completion with automatic fallback
        """
        # Try cassette first if in replay mode
        if self.cassette.mode == "replay":
            key = self._get_cassette_key(messages, "default", temperature)
            if response := self.cassette.get(key):
                logger.info(f"Using cassette response for key {key}")
                return response
        
        # Try providers in order
        providers_to_try = [preferred_provider] if preferred_provider else self.provider_order
        
        for provider_name in providers_to_try:
            if provider_name not in self.providers:
                continue
            
            provider = self.providers[provider_name]
            try:
                start_time = time.time()
                response = provider.complete(messages, temperature, max_tokens, timeout)
                duration = time.time() - start_time
                
                logger.info(f"{provider_name} completed in {duration:.2f}s")
                
                # Record to cassette if enabled
                if self.cassette.mode == "record":
                    key = self._get_cassette_key(messages, provider_name, temperature)
                    self.cassette.record(key, response)
                
                return response
                
            except Exception as e:
                logger.warning(f"{provider_name} failed: {e}")
                continue
        
        raise RuntimeError("All LLM providers failed")
    
    def complete_structured(
        self,
        messages: list[ChatCompletionMessageParam],
        response_model: Type[BaseModel],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
        preferred_provider: Optional[str] = None,
    ) -> BaseModel:
        """
        Generate structured completion with automatic fallback
        """
        # Try cassette first if in replay mode
        if self.cassette.mode == "replay":
            key = self._get_cassette_key(messages, response_model.__name__, temperature)
            if response_json := self.cassette.get(key):
                logger.info(f"Using cassette response for key {key}")
                return response_model.model_validate_json(response_json)
        
        # Try providers in order
        providers_to_try = [preferred_provider] if preferred_provider else self.provider_order
        
        for provider_name in providers_to_try:
            if provider_name not in self.providers:
                continue
            
            provider = self.providers[provider_name]
            try:
                start_time = time.time()
                response = provider.complete_structured(
                    messages, response_model, temperature, max_tokens, timeout
                )
                duration = time.time() - start_time
                
                logger.info(f"{provider_name} structured completed in {duration:.2f}s")
                
                # Record to cassette if enabled
                if self.cassette.mode == "record":
                    key = self._get_cassette_key(messages, response_model.__name__, temperature)
                    self.cassette.record(key, response.model_dump_json())
                
                return response
                
            except Exception as e:
                logger.warning(f"{provider_name} structured failed: {e}")
                continue
        
        raise RuntimeError("All LLM providers failed for structured completion")
