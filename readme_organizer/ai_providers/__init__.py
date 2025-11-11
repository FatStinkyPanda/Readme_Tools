"""AI provider adapters for README categorization and analysis."""

from .base_adapter import BaseAIAdapter
from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .ollama_adapter import OllamaAdapter
from .openrouter_adapter import OpenRouterAdapter
from .factory import get_ai_adapter

__all__ = [
    "BaseAIAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "OllamaAdapter",
    "OpenRouterAdapter",
    "get_ai_adapter",
]
