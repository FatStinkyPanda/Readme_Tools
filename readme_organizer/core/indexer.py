"""Indexing engine for README content."""

from typing import Any, Dict, List

from .categorizer import Categorizer
from .parser import ReadmeSection
from .storage import Storage


class Indexer:
    """Indexes README content for search and discovery."""

    def __init__(self, storage: Storage, categorizer: Categorizer) -> None:
        """Initialize indexer.

        Args:
            storage: Storage instance
            categorizer: Categorizer instance
        """
        self.storage = storage
        self.categorizer = categorizer

    async def index_readme(
        self,
        sections: List[ReadmeSection],
        custom_categories: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Index all sections of a README.

        Args:
            sections: List of sections to index
            custom_categories: Optional custom categories

        Returns:
            Dictionary with indexing statistics
        """
        stats = {
            "sections_indexed": 0,
            "categories_created": set(),
            "total_keywords": 0,
            "total_tags": 0,
        }

        # Ensure default categories exist
        category_ids = await self._ensure_categories(
            custom_categories or self.categorizer.default_categories
        )

        # Flatten sections for processing
        flat_sections = self._flatten_sections(sections)

        # Process each section
        for idx, section in enumerate(flat_sections):
            await self._index_section(section, idx, category_ids, stats)

        stats["categories_created"] = list(stats["categories_created"])
        return stats

    async def _ensure_categories(self, categories: List[str]) -> Dict[str, str]:
        """Ensure all categories exist in storage.

        Args:
            categories: List of category names

        Returns:
            Dictionary mapping category name to ID
        """
        category_ids = {}

        for category in categories:
            category_id = await self.storage.add_category(category)
            category_ids[category] = category_id

        return category_ids

    async def _index_section(
        self,
        section: ReadmeSection,
        order_index: int,
        category_ids: Dict[str, str],
        stats: Dict[str, Any],
    ) -> None:
        """Index a single section.

        Args:
            section: Section to index
            order_index: Order in document
            category_ids: Mapping of category name to ID
            stats: Statistics dictionary to update
        """
        # Skip empty sections
        if not section.content.strip():
            return

        # Categorize section
        categorization = await self.categorizer.categorize_section(section)
        category_name = categorization["category"]
        category_id = category_ids.get(category_name, list(category_ids.values())[0])

        # Extract metadata
        metadata = await self.categorizer.extract_metadata(section)

        # Add section to storage
        part_id = await self.storage.add_readme_part(
            title=section.title,
            content=section.content,
            category=category_id,
            order_index=order_index,
            metadata={
                "categorization": categorization,
                "summary": metadata.get("summary"),
                "char_count": metadata.get("char_count"),
                "word_count": metadata.get("word_count"),
                "level": section.level,
                "parent_title": section.parent_title,
            },
        )

        # Add keywords
        keywords = metadata.get("keywords", {})
        if keywords:
            await self.storage.add_keywords(part_id, keywords)
            stats["total_keywords"] += len(keywords)

        # Add tags
        tags = metadata.get("tags", [])
        if tags:
            await self.storage.add_tags(part_id, tags)
            stats["total_tags"] += len(tags)

        # Index for full-text search
        await self.storage.index_part(
            part_id=part_id,
            title=section.title,
            content=section.content,
            keywords=list(keywords.keys()),
            tags=tags,
            category=category_name,
        )

        stats["sections_indexed"] += 1
        stats["categories_created"].add(category_name)

    def _flatten_sections(self, sections: List[ReadmeSection]) -> List[ReadmeSection]:
        """Flatten hierarchical sections.

        Args:
            sections: Hierarchical sections

        Returns:
            Flattened list
        """
        flat = []
        for section in sections:
            flat.append(section)
            if section.children:
                flat.extend(self._flatten_sections(section.children))
        return flat

    async def reindex_section(self, part_id: str) -> None:
        """Reindex a specific section.

        Args:
            part_id: Section ID to reindex
        """
        # Get existing part
        part = await self.storage.get_part(part_id)
        if not part:
            raise ValueError(f"Part {part_id} not found")

        # Re-extract metadata
        section = ReadmeSection(
            title=part["title"],
            content=part["content"],
            level=part["metadata"].get("level", 1),
        )

        metadata = await self.categorizer.extract_metadata(section)

        # Update keywords and tags (would need delete methods in storage)
        # For now, this is a simplified version
        # In production, you'd want to delete old keywords/tags first

        keywords = metadata.get("keywords", {})
        if keywords:
            await self.storage.add_keywords(part_id, keywords)

        tags = metadata.get("tags", [])
        if tags:
            await self.storage.add_tags(part_id, tags)

    async def get_indexing_stats(self) -> Dict[str, Any]:
        """Get current indexing statistics.

        Returns:
            Dictionary with statistics
        """
        categories = await self.storage.get_all_categories()

        # Would need additional queries for comprehensive stats
        return {
            "total_categories": len(categories),
            "categories": [cat["name"] for cat in categories],
        }
