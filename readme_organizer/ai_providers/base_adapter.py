"""Base AI adapter interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseAIAdapter(ABC):
    """Base class for AI provider adapters."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> None:
        """Initialize AI adapter.

        Args:
            api_key: API key for the provider
            model: Model name to use
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional provider-specific arguments
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.kwargs = kwargs

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Optional[str] = None,
    ) -> str:
        """Generate a completion from the AI model.

        Args:
            prompt: User prompt
            system: Optional system message
            response_format: Optional response format ("json" or None)

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    async def categorize_section(
        self,
        content: str,
        available_categories: List[str],
    ) -> Dict[str, Any]:
        """Categorize a README section.

        Args:
            content: Section content
            available_categories: List of available categories

        Returns:
            Dictionary with category, confidence, and reasoning
        """
        pass

    @abstractmethod
    async def extract_keywords(
        self,
        content: str,
        max_keywords: int = 10,
    ) -> Dict[str, float]:
        """Extract keywords from content.

        Args:
            content: Section content
            max_keywords: Maximum number of keywords to extract

        Returns:
            Dictionary of keyword -> importance score
        """
        pass

    @abstractmethod
    async def generate_tags(
        self,
        content: str,
        max_tags: int = 5,
    ) -> List[str]:
        """Generate tags for content.

        Args:
            content: Section content
            max_tags: Maximum number of tags to generate

        Returns:
            List of tags
        """
        pass

    @abstractmethod
    async def summarize(
        self,
        content: str,
        max_sentences: int = 3,
    ) -> str:
        """Summarize content.

        Args:
            content: Content to summarize
            max_sentences: Maximum sentences in summary

        Returns:
            Summary text
        """
        pass

    def _format_categories(self, categories: List[str]) -> str:
        """Format categories for prompts.

        Args:
            categories: List of category names

        Returns:
            Formatted string
        """
        return ", ".join(categories)
