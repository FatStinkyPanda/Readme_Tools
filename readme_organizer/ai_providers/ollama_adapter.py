"""Ollama adapter for local AI-powered README analysis."""

import json
from typing import Any, Dict, List, Optional

import httpx

from .base_adapter import BaseAIAdapter


class OllamaAdapter(BaseAIAdapter):
    """Ollama local LLM adapter."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> None:
        """Initialize Ollama adapter.

        Args:
            base_url: Ollama server URL
            model: Model name (default: llama2)
            temperature: Sampling temperature
            **kwargs: Additional arguments
        """
        super().__init__(None, model, temperature, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Optional[str] = None,
    ) -> str:
        """Generate a completion from Ollama.

        Args:
            prompt: User prompt
            system: Optional system message
            response_format: Optional response format ("json" or None)

        Returns:
            Generated text
        """
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        if response_format == "json":
            full_prompt += "\n\nRespond only with valid JSON. Do not include any other text."

        request_data = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=request_data,
        )
        response.raise_for_status()

        result = response.json()
        return result.get("response", "")

    async def categorize_section(
        self,
        content: str,
        available_categories: List[str],
    ) -> Dict[str, Any]:
        """Categorize a README section using Ollama.

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
{content[:1500]}

Respond with JSON in this exact format (no other text):
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
                raise json.JSONDecodeError("No JSON found", response, 0)
        except (json.JSONDecodeError, ValueError):
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
        """Extract keywords from content using Ollama.

        Args:
            content: Section content
            max_keywords: Maximum number of keywords to extract

        Returns:
            Dictionary of keyword -> importance score
        """
        prompt = f"""Extract the {max_keywords} most relevant keywords from this README section.
Focus on technical terms, concepts, and important phrases.

Section:
{content[:1500]}

Respond with JSON in this exact format (no other text):
{{"keywords": ["keyword1", "keyword2"], "importance": {{"keyword1": 0.95, "keyword2": 0.85}}}}"""

        system = "You are an expert at extracting key technical terms from documentation."

        response = await self.complete(prompt, system=system, response_format="json")

        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
            else:
                return {}
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
        """Generate tags for content using Ollama.

        Args:
            content: Section content
            max_tags: Maximum number of tags to generate

        Returns:
            List of tags
        """
        prompt = f"""Generate {max_tags} short, descriptive tags for this README section.
Tags should be concise, relevant, and helpful for search (1-2 words each).

Section:
{content[:1500]}

Respond with JSON in this exact format (no other text):
{{"tags": ["tag1", "tag2", "tag3"]}}"""

        system = "You are an expert at creating searchable tags for documentation."

        response = await self.complete(prompt, system=system, response_format="json")

        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                return result.get("tags", [])[:max_tags]
        except (json.JSONDecodeError, ValueError):
            return []

        return []

    async def summarize(
        self,
        content: str,
        max_sentences: int = 3,
    ) -> str:
        """Summarize content using Ollama.

        Args:
            content: Content to summarize
            max_sentences: Maximum sentences in summary

        Returns:
            Summary text
        """
        prompt = f"""Create a brief summary of this README section ({max_sentences} sentences maximum).
Focus on the main purpose and key information.

Section:
{content[:2000]}

Provide only the summary, without any preamble."""

        system = "You are an expert at summarizing technical documentation concisely."

        return await self.complete(prompt, system=system)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
