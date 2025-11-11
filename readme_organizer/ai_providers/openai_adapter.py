"""OpenAI adapter for AI-powered README analysis."""

import json
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from .base_adapter import BaseAIAdapter


class OpenAIAdapter(BaseAIAdapter):
    """OpenAI GPT adapter."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> None:
        """Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4-turbo)
            temperature: Sampling temperature
            **kwargs: Additional OpenAI client arguments
        """
        super().__init__(api_key, model, temperature, **kwargs)
        self.client = AsyncOpenAI(api_key=api_key, **kwargs)

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Optional[str] = None,
    ) -> str:
        """Generate a completion from OpenAI.

        Args:
            prompt: User prompt
            system: Optional system message
            response_format: Optional response format ("json" or None)

        Returns:
            Generated text
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def categorize_section(
        self,
        content: str,
        available_categories: List[str],
    ) -> Dict[str, Any]:
        """Categorize a README section using OpenAI.

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
        result = json.loads(response)

        # Validate category is in available list
        if result.get("category") not in available_categories:
            # Find closest match or default to first category
            result["category"] = available_categories[0]
            result["confidence"] = 0.5

        return result

    async def extract_keywords(
        self,
        content: str,
        max_keywords: int = 10,
    ) -> Dict[str, float]:
        """Extract keywords from content using OpenAI.

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
        result = json.loads(response)

        keywords = result.get("keywords", [])
        importance = result.get("importance", {})

        # Ensure all keywords have importance scores
        return {kw: importance.get(kw, 0.5) for kw in keywords[:max_keywords]}

    async def generate_tags(
        self,
        content: str,
        max_tags: int = 5,
    ) -> List[str]:
        """Generate tags for content using OpenAI.

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
        result = json.loads(response)

        return result.get("tags", [])[:max_tags]

    async def summarize(
        self,
        content: str,
        max_sentences: int = 3,
    ) -> str:
        """Summarize content using OpenAI.

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
