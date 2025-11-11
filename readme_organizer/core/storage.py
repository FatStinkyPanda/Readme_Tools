"""Storage layer using SQLite with FTS5 full-text search."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiosqlite


class Storage:
    """SQLite storage with FTS5 full-text search support."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Establish database connection."""
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row
        await self._init_schema()

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _init_schema(self) -> None:
        """Initialize database schema."""
        if not self._connection:
            raise RuntimeError("Database not connected")

        # Categories table
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                parent_category TEXT,
                FOREIGN KEY (parent_category) REFERENCES categories(id)
            )
            """
        )

        # README parts table
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS readme_parts (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                parent_id TEXT,
                order_index INTEGER NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES readme_parts(id),
                FOREIGN KEY (category) REFERENCES categories(id)
            )
            """
        )

        # Keywords table
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id TEXT NOT NULL,
                keyword TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                FOREIGN KEY (part_id) REFERENCES readme_parts(id) ON DELETE CASCADE
            )
            """
        )

        # Create keyword index
        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword)
            """
        )

        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_keywords_part_id ON keywords(part_id)
            """
        )

        # Tags table
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY (part_id) REFERENCES readme_parts(id) ON DELETE CASCADE
            )
            """
        )

        # Create tag index
        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)
            """
        )

        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tags_part_id ON tags(part_id)
            """
        )

        # FTS5 virtual table for full-text search
        await self._connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                part_id UNINDEXED,
                title,
                content,
                keywords,
                tags,
                category,
                tokenize='porter unicode61'
            )
            """
        )

        await self._connection.commit()

    async def add_category(
        self,
        name: str,
        description: Optional[str] = None,
        parent_category: Optional[str] = None,
    ) -> str:
        """Add a new category.

        Args:
            name: Category name
            description: Optional description
            parent_category: Optional parent category ID

        Returns:
            Category ID
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        category_id = str(uuid4())
        await self._connection.execute(
            """
            INSERT INTO categories (id, name, description, parent_category)
            VALUES (?, ?, ?, ?)
            """,
            (category_id, name, description, parent_category),
        )
        await self._connection.commit()
        return category_id

    async def add_readme_part(
        self,
        title: str,
        content: str,
        category: str,
        parent_id: Optional[str] = None,
        order_index: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a new README part.

        Args:
            title: Part title
            content: Part content
            category: Category ID
            parent_id: Optional parent part ID
            order_index: Order in the document
            metadata: Optional metadata dictionary

        Returns:
            Part ID
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        part_id = str(uuid4())
        metadata_json = json.dumps(metadata) if metadata else None

        await self._connection.execute(
            """
            INSERT INTO readme_parts (
                id, title, content, category, parent_id, order_index, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (part_id, title, content, category, parent_id, order_index, metadata_json),
        )
        await self._connection.commit()
        return part_id

    async def add_keywords(self, part_id: str, keywords: Dict[str, float]) -> None:
        """Add keywords for a part.

        Args:
            part_id: README part ID
            keywords: Dictionary of keyword -> weight
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        for keyword, weight in keywords.items():
            await self._connection.execute(
                """
                INSERT INTO keywords (part_id, keyword, weight)
                VALUES (?, ?, ?)
                """,
                (part_id, keyword, weight),
            )
        await self._connection.commit()

    async def add_tags(self, part_id: str, tags: List[str]) -> None:
        """Add tags for a part.

        Args:
            part_id: README part ID
            tags: List of tags
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        for tag in tags:
            await self._connection.execute(
                """
                INSERT INTO tags (part_id, tag)
                VALUES (?, ?)
                """,
                (part_id, tag),
            )
        await self._connection.commit()

    async def index_part(
        self,
        part_id: str,
        title: str,
        content: str,
        keywords: List[str],
        tags: List[str],
        category: str,
    ) -> None:
        """Add part to FTS5 search index.

        Args:
            part_id: README part ID
            title: Part title
            content: Part content
            keywords: List of keywords
            tags: List of tags
            category: Category name
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        keywords_str = " ".join(keywords)
        tags_str = " ".join(tags)

        await self._connection.execute(
            """
            INSERT INTO search_index (part_id, title, content, keywords, tags, category)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (part_id, title, content, keywords_str, tags_str, category),
        )
        await self._connection.commit()

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Full-text search across all parts.

        Args:
            query: Search query
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            List of matching parts with relevance scores
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            """
            SELECT
                s.part_id,
                r.title,
                r.content,
                r.category,
                s.rank,
                snippet(search_index, 2, '<mark>', '</mark>', '...', 50) as snippet
            FROM search_index s
            JOIN readme_parts r ON s.part_id = r.id
            WHERE search_index MATCH ?
            ORDER BY rank
            LIMIT ? OFFSET ?
            """,
            (query, limit, offset),
        )

        rows = await cursor.fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "part_id": row["part_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "category": row["category"],
                    "rank": row["rank"],
                    "snippet": row["snippet"],
                }
            )

        return results

    async def get_part(self, part_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific README part.

        Args:
            part_id: Part ID

        Returns:
            Part data or None if not found
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            """
            SELECT * FROM readme_parts WHERE id = ?
            """,
            (part_id,),
        )

        row = await cursor.fetchone()
        if not row:
            return None

        return {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "category": row["category"],
            "parent_id": row["parent_id"],
            "order_index": row["order_index"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def get_keywords(self, part_id: str) -> Dict[str, float]:
        """Get keywords for a part.

        Args:
            part_id: Part ID

        Returns:
            Dictionary of keyword -> weight
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            """
            SELECT keyword, weight FROM keywords WHERE part_id = ?
            """,
            (part_id,),
        )

        rows = await cursor.fetchall()
        return {row["keyword"]: row["weight"] for row in rows}

    async def get_tags(self, part_id: str) -> List[str]:
        """Get tags for a part.

        Args:
            part_id: Part ID

        Returns:
            List of tags
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            """
            SELECT tag FROM tags WHERE part_id = ?
            """,
            (part_id,),
        )

        rows = await cursor.fetchall()
        return [row["tag"] for row in rows]

    async def get_all_categories(self) -> List[Dict[str, Any]]:
        """Get all categories.

        Returns:
            List of categories
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        cursor = await self._connection.execute(
            """
            SELECT * FROM categories ORDER BY name
            """
        )

        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "parent_category": row["parent_category"],
            }
            for row in rows
        ]

    async def clear_all(self) -> None:
        """Clear all data from the database."""
        if not self._connection:
            raise RuntimeError("Database not connected")

        await self._connection.execute("DELETE FROM search_index")
        await self._connection.execute("DELETE FROM tags")
        await self._connection.execute("DELETE FROM keywords")
        await self._connection.execute("DELETE FROM readme_parts")
        await self._connection.execute("DELETE FROM categories")
        await self._connection.commit()
