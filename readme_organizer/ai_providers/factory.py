"""Factory for creating AI adapters."""

from typing import Optional

from .base_adapter import BaseAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .ollama_adapter import OllamaAdapter
from .openai_adapter import OpenAIAdapter


def get_ai_adapter(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs,
) -> BaseAIAdapter:
    """Get an AI adapter instance.

    Args:
        provider: Provider name ("openai", "anthropic", or "ollama")
        api_key: API key (required for openai and anthropic)
        model: Model name (optional, uses default if not specified)
        base_url: Base URL (for ollama)
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

    elif provider == "ollama":
        return OllamaAdapter(
            base_url=base_url or "http://localhost:11434",
            model=model or "llama2",
            **kwargs,
        )

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Supported providers: openai, anthropic, ollama"
        )
