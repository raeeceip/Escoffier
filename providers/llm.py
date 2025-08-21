"""
LLM Provider system with real API integrations for OpenAI, Anthropic, Cohere, and Hugging Face.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
import asyncio
import logging
from datetime import datetime
import json

# LLM Client libraries
import openai
from anthropic import Anthropic
import cohere
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

from config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config.get("model", "unknown")
        self.max_tokens = config.get("max_tokens", 1000)
        self.temperature = config.get("temperature", 0.7)
    
    @abstractmethod
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass
    
    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model_name
    
    def format_kitchen_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Format prompt for kitchen assistant context."""
        system_message = (
            "You are a professional kitchen assistant AI working in a busy commercial kitchen. "
            "You must respond ONLY with valid JSON. Your responses should be practical, "
            "precise, and focused on kitchen operations. Consider food safety, efficiency, "
            "and coordination with other kitchen staff."
        )
        
        if context:
            context_str = f"\nContext: {json.dumps(context, indent=2)}"
        else:
            context_str = ""
        
        return f"{system_message}{context_str}\n\nRequest: {prompt}\n\nResponse (JSON only):"


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config["api_key"]
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        logger.info(f"OpenAI provider initialized with model: {self.model_name}")
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Generate response using OpenAI API."""
        try:
            formatted_prompt = self.format_kitchen_prompt(prompt, context)
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional kitchen assistant AI. Respond only with valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": formatted_prompt
                    }
                ],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                response_format={"type": "json_object"}
            )
            
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    return content.strip()
            
            raise ValueError("No response content received from OpenAI")
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Return a fallback JSON response
            return json.dumps({
                "error": "LLM_API_ERROR",
                "message": f"OpenAI API error: {str(e)}",
                "action": "fallback_response"
            })
    
    def get_provider_name(self) -> str:
        return "openai"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config["api_key"]
        self.client = Anthropic(api_key=self.api_key)
        logger.info(f"Anthropic provider initialized with model: {self.model_name}")
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Generate response using Anthropic API."""
        try:
            formatted_prompt = self.format_kitchen_prompt(prompt, context)
            
            # Anthropic uses synchronous client, wrap in asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.messages.create(
                    model=self.model_name,
                    max_tokens=kwargs.get("max_tokens", self.max_tokens),
                    temperature=kwargs.get("temperature", self.temperature),
                    messages=[
                        {
                            "role": "user",
                            "content": formatted_prompt
                        }
                    ]
                )
            )
            
            if response.content and len(response.content) > 0:
                content = response.content[0].text
                if content:
                    return content.strip()
            
            raise ValueError("No response content received from Anthropic")
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return json.dumps({
                "error": "LLM_API_ERROR",
                "message": f"Anthropic API error: {str(e)}",
                "action": "fallback_response"
            })
    
    def get_provider_name(self) -> str:
        return "anthropic"


class CohereProvider(LLMProvider):
    """Cohere provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config["api_key"]
        self.client = cohere.AsyncClient(api_key=self.api_key)
        logger.info(f"Cohere provider initialized with model: {self.model_name}")
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Generate response using Cohere API."""
        try:
            formatted_prompt = self.format_kitchen_prompt(prompt, context)
            
            response = await self.client.chat(
                model=self.model_name,
                message=formatted_prompt,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )
            
            if response.text:
                return response.text.strip()
            
            raise ValueError("No response text received from Cohere")
            
        except Exception as e:
            logger.error(f"Cohere API error: {e}")
            return json.dumps({
                "error": "LLM_API_ERROR", 
                "message": f"Cohere API error: {str(e)}",
                "action": "fallback_response"
            })
    
    def get_provider_name(self) -> str:
        return "cohere"


class HuggingFaceProvider(LLMProvider):
    """Hugging Face local model provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.cache_dir = config.get("cache_dir", "./models")
        self.device = config.get("device", "auto")
        self.pipeline = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load the Hugging Face model."""
        try:
            logger.info(f"Loading Hugging Face model: {self.model_name}")
            
            # Determine device
            if self.device == "auto":
                device = 0 if torch.cuda.is_available() else -1
            else:
                device = self.device
            
            # Load tokenizer and pipeline
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            
            # Add pad token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.pipeline = pipeline(
                "text-generation",
                model=self.model_name,
                tokenizer=self.tokenizer,
                device=device,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            
            logger.info(f"Hugging Face model loaded successfully on device: {device}")
            
        except Exception as e:
            logger.error(f"Failed to load Hugging Face model: {e}")
            self.pipeline = None
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Generate response using local Hugging Face model."""
        if not self.pipeline:
            return json.dumps({
                "error": "MODEL_NOT_LOADED",
                "message": "Hugging Face model not available",
                "action": "fallback_response"
            })
        
        try:
            formatted_prompt = self.format_kitchen_prompt(prompt, context)
            
            # Run in thread pool to avoid blocking
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.pipeline(
                    formatted_prompt,
                    max_new_tokens=kwargs.get("max_tokens", self.max_tokens),
                    temperature=kwargs.get("temperature", self.temperature),
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    return_full_text=False
                )
            )
            
            if response and len(response) > 0:
                generated_text = response[0]["generated_text"]
                return generated_text.strip()
            
            raise ValueError("No response generated from Hugging Face model")
            
        except Exception as e:
            logger.error(f"Hugging Face generation error: {e}")
            return json.dumps({
                "error": "GENERATION_ERROR",
                "message": f"Local model error: {str(e)}",
                "action": "fallback_response"
            })
    
    def get_provider_name(self) -> str:
        return "huggingface"


class LLMProviderManager:
    """Manager for multiple LLM providers."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.providers: Dict[str, LLMProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available LLM providers."""
        
        # OpenAI
        if self.settings.openai.enabled and self.settings.openai.api_key:
            try:
                self.providers["openai"] = OpenAIProvider({
                    "api_key": self.settings.openai.api_key,
                    "model": self.settings.openai.model,
                    "base_url": self.settings.openai.base_url,
                    "max_tokens": self.settings.openai.max_tokens,
                    "temperature": self.settings.openai.temperature
                })
                logger.info("OpenAI provider registered")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI provider: {e}")
        
        # Anthropic
        if self.settings.anthropic.enabled and self.settings.anthropic.api_key:
            try:
                self.providers["anthropic"] = AnthropicProvider({
                    "api_key": self.settings.anthropic.api_key,
                    "model": self.settings.anthropic.model,
                    "max_tokens": self.settings.anthropic.max_tokens,
                    "temperature": self.settings.anthropic.temperature
                })
                logger.info("Anthropic provider registered")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic provider: {e}")
        
        # Cohere
        if self.settings.cohere.enabled and self.settings.cohere.api_key:
            try:
                self.providers["cohere"] = CohereProvider({
                    "api_key": self.settings.cohere.api_key,
                    "model": self.settings.cohere.model,
                    "max_tokens": self.settings.cohere.max_tokens,
                    "temperature": self.settings.cohere.temperature
                })
                logger.info("Cohere provider registered")
            except Exception as e:
                logger.error(f"Failed to initialize Cohere provider: {e}")
        
        # Hugging Face
        if self.settings.huggingface.enabled:
            try:
                self.providers["huggingface"] = HuggingFaceProvider({
                    "model": self.settings.huggingface.default_model,
                    "cache_dir": self.settings.huggingface.cache_dir,
                    "device": self.settings.huggingface.device,
                    "max_tokens": 500,  # Conservative for local models
                    "temperature": 0.7
                })
                logger.info("Hugging Face provider registered")
            except Exception as e:
                logger.error(f"Failed to initialize Hugging Face provider: {e}")
    
    def get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Get a specific provider by name."""
        return self.providers.get(provider_name)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self.providers.keys())
    
    def get_default_provider(self) -> Optional[LLMProvider]:
        """Get the default provider (first available)."""
        if not self.providers:
            return None
        return next(iter(self.providers.values()))
    
    async def generate_response(
        self,
        prompt: str,
        provider_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> tuple[str, str]:
        """Generate response using specified or default provider."""
        
        if provider_name:
            provider = self.get_provider(provider_name)
            if not provider:
                raise ValueError(f"Provider '{provider_name}' not available")
        else:
            provider = self.get_default_provider()
            if not provider:
                raise ValueError("No LLM providers available")
        
        response = await provider.generate_response(prompt, context, **kwargs)
        return response, provider.get_provider_name()
    
    def add_provider(self, name: str, provider: LLMProvider) -> None:
        """Add a custom provider."""
        self.providers[name] = provider
        logger.info(f"Custom provider '{name}' added")
    
    def remove_provider(self, name: str) -> None:
        """Remove a provider."""
        if name in self.providers:
            del self.providers[name]
            logger.info(f"Provider '{name}' removed")


# Global provider manager instance
_provider_manager: Optional[LLMProviderManager] = None


def get_llm_manager(settings: Optional[Settings] = None) -> LLMProviderManager:
    """Get LLM provider manager singleton."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = LLMProviderManager(settings)
    return _provider_manager


# Backwards compatibility alias
get_llm_provider = get_llm_manager