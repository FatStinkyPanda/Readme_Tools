"""Search engine for README discovery."""

from typing import Any, Dict, List, Optional

from .storage import Storage


class SearchEngine:
    """Search engine for README content."""

    def __init__(self, storage: Storage) -> None:
        """Initialize search engine.

        Args:
            storage: Storage instance
        """
        self.storage = storage

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Full-text search across README content.

        Args:
            query: Search query
            filters: Optional filters (category, tags, keywords)
            limit: Maximum results
            offset: Result offset for pagination

        Returns:
            Search results with metadata
        """
        # Perform full-text search
        results = await self.storage.search(query, limit=limit, offset=offset)

        # Enrich results with additional metadata
        enriched_results = []
        for result in results:
            part_id = result["part_id"]

            # Get keywords and tags
            keywords = await self.storage.get_keywords(part_id)
            tags = await self.storage.get_tags(part_id)

            enriched_result = {
                **result,
                "keywords": keywords,
                "tags": tags,
            }

            # Apply filters if provided
            if filters and not self._matches_filters(enriched_result, filters):
                continue

            enriched_results.append(enriched_result)

        return {
            "query": query,
            "total": len(enriched_results),
            "results": enriched_results,
            "limit": limit,
            "offset": offset,
        }

    async def search_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search by keywords.

        Args:
            keywords: List of keywords to search for
            limit: Maximum results

        Returns:
            List of matching parts
        """
        if not self.storage._connection:
            raise RuntimeError("Database not connected")

        # Build query for keyword search
        placeholders = " OR ".join(["keyword = ?"] * len(keywords))
        query = f"""
            SELECT DISTINCT
                r.id as part_id,
                r.title,
                r.content,
                r.category,
                COUNT(k.keyword) as keyword_matches,
                SUM(k.weight) as total_weight
            FROM readme_parts r
            JOIN keywords k ON r.id = k.part_id
            WHERE {placeholders}
            GROUP BY r.id
            ORDER BY total_weight DESC, keyword_matches DESC
            LIMIT ?
        """

        cursor = await self.storage._connection.execute(query, (*keywords, limit))
        rows = await cursor.fetchall()

        results = []
        for row in rows:
            part_keywords = await self.storage.get_keywords(row["part_id"])
            part_tags = await self.storage.get_tags(row["part_id"])

            results.append(
                {
                    "part_id": row["part_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "category": row["category"],
                    "keyword_matches": row["keyword_matches"],
                    "total_weight": row["total_weight"],
                    "keywords": part_keywords,
                    "tags": part_tags,
                }
            )

        return results

    async def search_by_tags(
        self, tags: List[str], match_all: bool = False, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search by tags.

        Args:
            tags: List of tags to search for
            match_all: If True, require all tags; if False, match any tag
            limit: Maximum results

        Returns:
            List of matching parts
        """
        if not self.storage._connection:
            raise RuntimeError("Database not connected")

        if match_all:
            # Require all tags
            query = f"""
                SELECT
                    r.id as part_id,
                    r.title,
                    r.content,
                    r.category,
                    COUNT(DISTINCT t.tag) as tag_matches
                FROM readme_parts r
                JOIN tags t ON r.id = t.part_id
                WHERE t.tag IN ({','.join(['?'] * len(tags))})
                GROUP BY r.id
                HAVING tag_matches = ?
                LIMIT ?
            """
            params = (*tags, len(tags), limit)
        else:
            # Match any tag
            query = f"""
                SELECT DISTINCT
                    r.id as part_id,
                    r.title,
                    r.content,
                    r.category,
                    COUNT(t.tag) as tag_matches
                FROM readme_parts r
                JOIN tags t ON r.id = t.part_id
                WHERE t.tag IN ({','.join(['?'] * len(tags))})
                GROUP BY r.id
                ORDER BY tag_matches DESC
                LIMIT ?
            """
            params = (*tags, limit)

        cursor = await self.storage._connection.execute(query, params)
        rows = await cursor.fetchall()

        results = []
        for row in rows:
            part_keywords = await self.storage.get_keywords(row["part_id"])
            part_tags = await self.storage.get_tags(row["part_id"])

            results.append(
                {
                    "part_id": row["part_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "category": row["category"],
                    "tag_matches": row["tag_matches"],
                    "keywords": part_keywords,
                    "tags": part_tags,
                }
            )

        return results

    async def search_by_category(
        self, category: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search by category.

        Args:
            category: Category name or ID
            limit: Maximum results

        Returns:
            List of parts in category
        """
        if not self.storage._connection:
            raise RuntimeError("Database not connected")

        # Search by category name or ID
        query = """
            SELECT
                r.id as part_id,
                r.title,
                r.content,
                r.category,
                r.order_index
            FROM readme_parts r
            JOIN categories c ON r.category = c.id
            WHERE c.name = ? OR c.id = ?
            ORDER BY r.order_index
            LIMIT ?
        """

        cursor = await self.storage._connection.execute(query, (category, category, limit))
        rows = await cursor.fetchall()

        results = []
        for row in rows:
            part_keywords = await self.storage.get_keywords(row["part_id"])
            part_tags = await self.storage.get_tags(row["part_id"])

            results.append(
                {
                    "part_id": row["part_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "category": row["category"],
                    "keywords": part_keywords,
                    "tags": part_tags,
                }
            )

        return results

    async def get_related_sections(
        self, part_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find sections related to a given section.

        Args:
            part_id: Section ID
            limit: Maximum results

        Returns:
            List of related sections
        """
        # Get keywords and tags for the part
        keywords = await self.storage.get_keywords(part_id)
        tags = await self.storage.get_tags(part_id)

        if not keywords and not tags:
            return []

        # Search by keywords and tags
        keyword_results = []
        if keywords:
            keyword_results = await self.search_by_keywords(
                list(keywords.keys()), limit=limit * 2
            )

        tag_results = []
        if tags:
            tag_results = await self.search_by_tags(tags, match_all=False, limit=limit * 2)

        # Combine and deduplicate
        seen = {part_id}  # Exclude the original section
        related = []

        for result in keyword_results + tag_results:
            if result["part_id"] not in seen:
                related.append(result)
                seen.add(result["part_id"])

            if len(related) >= limit:
                break

        return related

    def _matches_filters(self, result: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if a result matches the given filters.

        Args:
            result: Search result
            filters: Filter criteria

        Returns:
            True if matches, False otherwise
        """
        if "category" in filters:
            if result["category"] != filters["category"]:
                return False

        if "tags" in filters:
            required_tags = set(filters["tags"])
            result_tags = set(result.get("tags", []))
            if not required_tags.issubset(result_tags):
                return False

        if "keywords" in filters:
            required_keywords = set(filters["keywords"])
            result_keywords = set(result.get("keywords", {}).keys())
            if not required_keywords.issubset(result_keywords):
                return False

        return True

    async def get_all_keywords(self) -> Dict[str, int]:
        """Get all keywords with usage counts.

        Returns:
            Dictionary of keyword -> count
        """
        if not self.storage._connection:
            raise RuntimeError("Database not connected")

        query = """
            SELECT keyword, COUNT(*) as count
            FROM keywords
            GROUP BY keyword
            ORDER BY count DESC
        """

        cursor = await self.storage._connection.execute(query)
        rows = await cursor.fetchall()

        return {row["keyword"]: row["count"] for row in rows}

    async def get_all_tags(self) -> Dict[str, int]:
        """Get all tags with usage counts.

        Returns:
            Dictionary of tag -> count
        """
        if not self.storage._connection:
            raise RuntimeError("Database not connected")

        query = """
            SELECT tag, COUNT(*) as count
            FROM tags
            GROUP BY tag
            ORDER BY count DESC
        """

        cursor = await self.storage._connection.execute(query)
        rows = await cursor.fetchall()

        return {row["tag"]: row["count"] for row in rows}
