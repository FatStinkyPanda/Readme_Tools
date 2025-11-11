"""Anthropic Claude adapter for AI-powered README analysis."""

import json
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from .base_adapter import BaseAIAdapter


class AnthropicAdapter(BaseAIAdapter):
    """Anthropic Claude adapter."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> None:
        """Initialize Anthropic adapter.

        Args:
            api_key: Anthropic API key
            model: Model name (default: claude-3-sonnet-20240229)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic client arguments
        """
        super().__init__(api_key, model, temperature, **kwargs)
        self.client = AsyncAnthropic(api_key=api_key, **kwargs)
        self.max_tokens = max_tokens

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Optional[str] = None,
    ) -> str:
        """Generate a completion from Anthropic Claude.

        Args:
            prompt: User prompt
            system: Optional system message
            response_format: Optional response format ("json" or None)

        Returns:
            Generated text
        """
        messages = [{"role": "user", "content": prompt}]

        if response_format == "json":
            prompt += "\n\nRespond only with valid JSON. Do not include any other text."

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if system:
            kwargs["system"] = system

        response = await self.client.messages.create(**kwargs)
        return response.content[0].text

    async def categorize_section(
        self,
        content: str,
        available_categories: List[str],
    ) -> Dict[str, Any]:
        """Categorize a README section using Claude.

        Args:
            content: Section content
            available_categories: List of available categories

        Returns:
            Dictionary with category, confidence, and reasoning
        """
        categories_str = self._format_categories(available_categories)

        prompt = f"""Analyze the following README section and determine its category.
Consider the content, headings, and context.

Available categories: {categories_str}

Section:
{content[:2000]}

Respond with JSON in this exact format:
{{"category": "category_name", "confidence": 0.95, "reasoning": "brief explanation"}}"""

        system = "You are an expert at analyzing and categorizing technical documentation."

        response = await self.complete(prompt, system=system, response_format="json")

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            result = {
                "category": available_categories[0],
                "confidence": 0.5,
                "reasoning": "Failed to parse AI response",
            }

        # Validate category is in available list
        if result.get("category") not in available_categories:
            result["category"] = available_categories[0]
            result["confidence"] = 0.5

        return result

    async def extract_keywords(
        self,
        content: str,
        max_keywords: int = 10,
    ) -> Dict[str, float]:
        """Extract keywords from content using Claude.

        Args:
            content: Section content
            max_keywords: Maximum number of keywords to extract

        Returns:
            Dictionary of keyword -> importance score
        """
        prompt = f"""Extract the {max_keywords} most relevant keywords from this README section.
Focus on technical terms, concepts, and important phrases.

Section:
{content[:2000]}

Respond with JSON in this exact format:
{{"keywords": ["keyword1", "keyword2"], "importance": {{"keyword1": 0.95, "keyword2": 0.85}}}}"""

        system = "You are an expert at extracting key technical terms from documentation."

        response = await self.complete(prompt, system=system, response_format="json")

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            return {}

        keywords = result.get("keywords", [])
        importance = result.get("importance", {})

        return {kw: importance.get(kw, 0.5) for kw in keywords[:max_keywords]}

    async def generate_tags(
        self,
        content: str,
        max_tags: int = 5,
    ) -> List[str]:
        """Generate tags for content using Claude.

        Args:
            content: Section content
            max_tags: Maximum number of tags to generate

        Returns:
            List of tags
        """
        prompt = f"""Generate {max_tags} short, descriptive tags for this README section.
Tags should be concise, relevant, and helpful for search (1-2 words each).

Section:
{content[:2000]}

Respond with JSON in this exact format:
{{"tags": ["tag1", "tag2", "tag3"]}}"""

        system = "You are an expert at creating searchable tags for documentation."

        response = await self.complete(prompt, system=system, response_format="json")

        try:
            result = json.loads(response)
            return result.get("tags", [])[:max_tags]
        except json.JSONDecodeError:
            return []

    async def summarize(
        self,
        content: str,
        max_sentences: int = 3,
    ) -> str:
        """Summarize content using Claude.

        Args:
            content: Content to summarize
            max_sentences: Maximum sentences in summary

        Returns:
            Summary text
        """
        prompt = f"""Create a brief summary of this README section ({max_sentences} sentences maximum).
Focus on the main purpose and key information.

Section:
{content[:3000]}

Provide only the summary, without any preamble."""

        system = "You are an expert at summarizing technical documentation concisely."

        return await self.complete(prompt, system=system)
