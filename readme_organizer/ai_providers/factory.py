"""Factory for creating AI adapters."""

from typing import Optional

from .base_adapter import BaseAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .ollama_adapter import OllamaAdapter
from .openai_adapter import OpenAIAdapter
from .openrouter_adapter import OpenRouterAdapter


def get_ai_adapter(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs,
) -> BaseAIAdapter:
    """Get an AI adapter instance.

    Args:
        provider: Provider name ("openai", "anthropic", "openrouter", or "ollama")
        api_key: API key (required for openai, anthropic, and openrouter)
        model: Model name (optional, uses default if not specified)
        base_url: Base URL (for ollama or custom endpoints)
        **kwargs: Additional provider-specific arguments

    Returns:
        AI adapter instance

    Raises:
        ValueError: If provider is unknown or required parameters are missing
    """
    provider = provider.lower()

    if provider == "openai":
        if not api_key:
            raise ValueError("API key required for OpenAI provider")
        return OpenAIAdapter(
            api_key=api_key,
            model=model or "gpt-4-turbo",
            **kwargs,
        )

    elif provider == "anthropic":
        if not api_key:
            raise ValueError("API key required for Anthropic provider")
        return AnthropicAdapter(
            api_key=api_key,
            model=model or "claude-3-sonnet-20240229",
            **kwargs,
        )

    elif provider == "openrouter":
        if not api_key:
            raise ValueError("API key required for OpenRouter provider")
        return OpenRouterAdapter(
            api_key=api_key,
            model=model or "anthropic/claude-3-sonnet",
            base_url=base_url or "https://openrouter.ai/api/v1",
            **kwargs,
        )

    elif provider == "ollama":
        return OllamaAdapter(
            base_url=base_url or "http://localhost:11434",
            model=model or "llama2",
            **kwargs,
        )

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Supported providers: openai, anthropic, openrouter, ollama"
        )
