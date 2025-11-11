"""AI-powered categorization of README sections."""

from typing import Any, Dict, List

from ..ai_providers.base_adapter import BaseAIAdapter
from .parser import ReadmeSection


class Categorizer:
    """Categorizes README sections using AI."""

    def __init__(
        self,
        ai_adapter: BaseAIAdapter,
        default_categories: List[str] | None = None,
    ) -> None:
        """Initialize categorizer.

        Args:
            ai_adapter: AI adapter for categorization
            default_categories: Default categories to use
        """
        self.ai_adapter = ai_adapter
        self.default_categories = default_categories or [
            "installation",
            "configuration",
            "usage",
            "api",
            "development",
            "testing",
            "deployment",
            "troubleshooting",
            "contributing",
            "license",
            "overview",
            "features",
            "examples",
            "reference",
        ]

    async def categorize_section(
        self, section: ReadmeSection, custom_categories: List[str] | None = None
    ) -> Dict[str, Any]:
        """Categorize a README section.

        Args:
            section: Section to categorize
            custom_categories: Optional custom categories

        Returns:
            Dictionary with category, confidence, and reasoning
        """
        categories = custom_categories or self.default_categories

        # Try to infer category from title first
        title_category = self._infer_category_from_title(section.title, categories)
        if title_category:
            return {
                "category": title_category,
                "confidence": 0.9,
                "reasoning": f"Inferred from title: {section.title}",
            }

        # Use AI for categorization
        content = f"# {section.title}\n\n{section.content}"
        result = await self.ai_adapter.categorize_section(content, categories)

        return result

    async def extract_metadata(self, section: ReadmeSection) -> Dict[str, Any]:
        """Extract full metadata for a section.

        Args:
            section: Section to analyze

        Returns:
            Dictionary with all metadata (keywords, tags, summary, etc.)
        """
        content = f"# {section.title}\n\n{section.content}"

        # Extract in parallel would be ideal, but sequential is safer
        keywords = await self.ai_adapter.extract_keywords(content)
        tags = await self.ai_adapter.generate_tags(content)
        summary = await self.ai_adapter.summarize(content)

        return {
            "keywords": keywords,
            "tags": tags,
            "summary": summary,
            "char_count": len(section.content),
            "word_count": len(section.content.split()),
        }

    def _infer_category_from_title(
        self, title: str, categories: List[str]
    ) -> str | None:
        """Try to infer category from section title.

        Args:
            title: Section title
            categories: Available categories

        Returns:
            Category if inferred, None otherwise
        """
        title_lower = title.lower()

        # Direct matches
        for category in categories:
            if category in title_lower:
                return category

        # Common patterns
        patterns = {
            "install": "installation",
            "setup": "installation",
            "getting started": "installation",
            "quick start": "installation",
            "config": "configuration",
            "settings": "configuration",
            "how to": "usage",
            "guide": "usage",
            "tutorial": "usage",
            "example": "examples",
            "api reference": "api",
            "endpoints": "api",
            "test": "testing",
            "develop": "development",
            "build": "development",
            "deploy": "deployment",
            "contribute": "contributing",
            "license": "license",
            "trouble": "troubleshooting",
            "faq": "troubleshooting",
            "about": "overview",
            "introduction": "overview",
            "feature": "features",
        }

        for pattern, category in patterns.items():
            if pattern in title_lower and category in categories:
                return category

        return None

    async def categorize_all(
        self, sections: List[ReadmeSection], custom_categories: List[str] | None = None
    ) -> Dict[str, Dict[str, Any]]:
        """Categorize all sections.

        Args:
            sections: List of sections to categorize
            custom_categories: Optional custom categories

        Returns:
            Dictionary mapping section title to categorization result
        """
        results = {}

        for section in sections:
            result = await self.categorize_section(section, custom_categories)
            results[section.title] = result

        return results
