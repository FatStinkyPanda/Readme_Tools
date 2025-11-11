"""OpenRouter adapter for AI-powered README analysis.

OpenRouter provides unified access to multiple AI models through a single API.
"""

import json
from typing import Any, Dict, List, Optional

import httpx

from .base_adapter import BaseAIAdapter


class OpenRouterAdapter(BaseAIAdapter):
    """OpenRouter adapter for accessing multiple AI models."""

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-3-sonnet",
        temperature: float = 0.7,
        base_url: str = "https://openrouter.ai/api/v1",
        site_url: Optional[str] = None,
        app_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize OpenRouter adapter.

        Args:
            api_key: OpenRouter API key
            model: Model name (default: anthropic/claude-3-sonnet)
                   See https://openrouter.ai/models for available models
            temperature: Sampling temperature
            base_url: OpenRouter API base URL
            site_url: Your site URL (for rankings)
            app_name: Your app name (for rankings)
            **kwargs: Additional arguments
        """
        super().__init__(api_key, model, temperature, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.site_url = site_url or "https://github.com/FatStinkyPanda/Readme_Tools"
        self.app_name = app_name or "README Tools"
        self.client = httpx.AsyncClient(timeout=120.0)

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Optional[str] = None,
    ) -> str:
        """Generate a completion from OpenRouter.

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

        if response_format == "json":
            prompt += "\n\nRespond only with valid JSON. Do not include any other text."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
            "Content-Type": "application/json",
        }

        request_data = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        # Add response format for compatible models
        if response_format == "json" and self._supports_json_mode():
            request_data["response_format"] = {"type": "json_object"}

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=request_data,
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    async def categorize_section(
        self,
        content: str,
        available_categories: List[str],
    ) -> Dict[str, Any]:
        """Categorize a README section using OpenRouter.

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
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
            else:
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
        """Extract keywords from content using OpenRouter.

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
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
            else:
                result = json.loads(response)
        except (json.JSONDecodeError, ValueError):
            return {}

        keywords = result.get("keywords", [])
        importance = result.get("importance", {})

        return {kw: importance.get(kw, 0.5) for kw in keywords[:max_keywords]}

    async def generate_tags(
        self,
        content: str,
        max_tags: int = 5,
    ) -> List[str]:
        """Generate tags for content using OpenRouter.

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
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
            else:
                result = json.loads(response)
            return result.get("tags", [])[:max_tags]
        except (json.JSONDecodeError, ValueError):
            return []

    async def summarize(
        self,
        content: str,
        max_sentences: int = 3,
    ) -> str:
        """Summarize content using OpenRouter.

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

    def _supports_json_mode(self) -> bool:
        """Check if the current model supports JSON mode.

        Returns:
            True if model supports JSON mode
        """
        # Models that support JSON mode
        json_mode_models = [
            "openai/gpt-4-turbo",
            "openai/gpt-4-turbo-preview",
            "openai/gpt-3.5-turbo",
            "anthropic/claude-3",
            "anthropic/claude-3-opus",
            "anthropic/claude-3-sonnet",
            "anthropic/claude-3-haiku",
        ]

        model_lower = self.model.lower()
        return any(supported in model_lower for supported in json_mode_models)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
