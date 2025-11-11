"""Context provider for AI agents."""

import json
from typing import Any, Dict, List, Optional

from .search import SearchEngine
from .storage import Storage


class ContextProvider:
    """Provides relevant README context to AI agents."""

    def __init__(
        self,
        storage: Storage,
        search_engine: SearchEngine,
        max_tokens: int = 4000,
    ) -> None:
        """Initialize context provider.

        Args:
            storage: Storage instance
            search_engine: Search engine instance
            max_tokens: Maximum tokens to return
        """
        self.storage = storage
        self.search_engine = search_engine
        self.max_tokens = max_tokens

    async def get_context(
        self,
        query: str,
        max_tokens: Optional[int] = None,
        include_related: bool = True,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get relevant context for a query.

        Args:
            query: Query or topic
            max_tokens: Maximum tokens (defaults to instance max_tokens)
            include_related: Whether to include related sections
            categories: Optional category filter

        Returns:
            Dictionary with context sections and metadata
        """
        max_tokens = max_tokens or self.max_tokens

        # Search for relevant sections
        search_results = await self.search_engine.search(
            query, filters={"category": categories[0]} if categories else None, limit=20
        )

        # Select and format sections to fit token limit
        selected_sections = self._select_sections(
            search_results["results"], max_tokens, include_related
        )

        # Format context for AI agent
        context = self._format_context(selected_sections)

        return {
            "query": query,
            "context": context,
            "sections": selected_sections,
            "token_estimate": self._estimate_tokens(context),
            "sections_included": len(selected_sections),
        }

    async def get_context_by_category(
        self, category: str, max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get context for a specific category.

        Args:
            category: Category name
            max_tokens: Maximum tokens

        Returns:
            Dictionary with category context
        """
        max_tokens = max_tokens or self.max_tokens

        # Get all sections in category
        sections = await self.search_engine.search_by_category(category, limit=50)

        # Select sections to fit token limit
        selected_sections = self._select_sections(sections, max_tokens, include_related=False)

        # Format context
        context = self._format_context(selected_sections)

        return {
            "category": category,
            "context": context,
            "sections": selected_sections,
            "token_estimate": self._estimate_tokens(context),
            "sections_included": len(selected_sections),
        }

    async def get_context_by_tags(
        self, tags: List[str], max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get context for specific tags.

        Args:
            tags: List of tags
            max_tokens: Maximum tokens

        Returns:
            Dictionary with tagged context
        """
        max_tokens = max_tokens or self.max_tokens

        # Search by tags
        sections = await self.search_engine.search_by_tags(tags, match_all=False, limit=50)

        # Select sections
        selected_sections = self._select_sections(sections, max_tokens, include_related=False)

        # Format context
        context = self._format_context(selected_sections)

        return {
            "tags": tags,
            "context": context,
            "sections": selected_sections,
            "token_estimate": self._estimate_tokens(context),
            "sections_included": len(selected_sections),
        }

    async def get_progressive_context(
        self, query: str, step_tokens: int = 1000, max_steps: int = 4
    ) -> List[Dict[str, Any]]:
        """Get context progressively in steps.

        Useful for AI agents that can request more context as needed.

        Args:
            query: Query or topic
            step_tokens: Tokens per step
            max_steps: Maximum steps

        Returns:
            List of context chunks
        """
        # Get all relevant sections
        search_results = await self.search_engine.search(query, limit=50)
        sections = search_results["results"]

        steps = []
        current_tokens = 0

        for i in range(max_steps):
            # Calculate remaining tokens
            remaining = step_tokens

            # Select sections for this step
            step_sections = []
            for section in sections:
                section_tokens = self._estimate_tokens(section["content"])

                if current_tokens + section_tokens <= (i + 1) * step_tokens:
                    if section not in [s for step in steps for s in step.get("sections", [])]:
                        step_sections.append(section)
                        current_tokens += section_tokens

                if len(step_sections) >= 3:  # Limit sections per step
                    break

            if not step_sections:
                break

            # Format step
            context = self._format_context(step_sections)
            steps.append(
                {
                    "step": i + 1,
                    "context": context,
                    "sections": step_sections,
                    "token_estimate": self._estimate_tokens(context),
                }
            )

        return steps

    def _select_sections(
        self,
        sections: List[Dict[str, Any]],
        max_tokens: int,
        include_related: bool,
    ) -> List[Dict[str, Any]]:
        """Select sections to fit within token limit.

        Args:
            sections: Available sections
            max_tokens: Maximum tokens
            include_related: Whether to include related sections

        Returns:
            Selected sections
        """
        selected = []
        current_tokens = 0

        # Sort by relevance (rank or keyword matches)
        sorted_sections = sorted(
            sections,
            key=lambda x: x.get("rank", 0) or x.get("total_weight", 0) or x.get("keyword_matches", 0),
            reverse=True,
        )

        for section in sorted_sections:
            # Estimate tokens for this section
            section_tokens = self._estimate_tokens(
                f"# {section['title']}\n\n{section['content']}"
            )

            # Check if it fits
            if current_tokens + section_tokens <= max_tokens:
                selected.append(section)
                current_tokens += section_tokens
            else:
                break

        return selected

    def _format_context(self, sections: List[Dict[str, Any]]) -> str:
        """Format sections into context string.

        Args:
            sections: Sections to format

        Returns:
            Formatted context string
        """
        if not sections:
            return "No relevant context found."

        context_parts = []

        for section in sections:
            # Format section with metadata
            part = f"## {section['title']}\n\n"

            # Add metadata if useful
            if section.get("tags"):
                part += f"*Tags: {', '.join(section['tags'])}*\n\n"

            part += section["content"]
            context_parts.append(part)

        return "\n\n---\n\n".join(context_parts)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses a simple approximation: ~4 characters per token.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4

    async def get_summary(self) -> Dict[str, Any]:
        """Get summary of available context.

        Returns:
            Dictionary with summary statistics
        """
        categories = await self.storage.get_all_categories()
        all_keywords = await self.search_engine.get_all_keywords()
        all_tags = await self.search_engine.get_all_tags()

        return {
            "total_categories": len(categories),
            "categories": [cat["name"] for cat in categories],
            "total_keywords": len(all_keywords),
            "top_keywords": dict(list(all_keywords.items())[:20]),
            "total_tags": len(all_tags),
            "top_tags": dict(list(all_tags.items())[:20]),
        }
