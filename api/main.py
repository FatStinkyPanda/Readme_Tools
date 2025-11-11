"""Main FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from readme_organizer.ai_providers.factory import get_ai_adapter
from readme_organizer.core.categorizer import Categorizer
from readme_organizer.core.context_provider import ContextProvider
from readme_organizer.core.indexer import Indexer
from readme_organizer.core.parser import Parser
from readme_organizer.core.search import SearchEngine
from readme_organizer.core.storage import Storage

from .models import (
    ContextRequest,
    ContextResponse,
    ContextSection,
    ErrorResponse,
    HealthResponse,
    KeywordSearchRequest,
    ParseReadmeRequest,
    ParseResponse,
    ReadmePart,
    SearchRequest,
    SearchResponse,
    SearchResult,
    StatsResponse,
    TagSearchRequest,
)

# Global instances
storage: Storage = None
search_engine: SearchEngine = None
context_provider: ContextProvider = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global storage, search_engine, context_provider

    settings = get_settings()
    settings.ensure_data_directory()

    # Initialize storage
    storage = Storage(settings.database_path)
    await storage.connect()

    # Initialize other components
    search_engine = SearchEngine(storage)
    context_provider = ContextProvider(
        storage, search_engine, max_tokens=settings.default_max_context_tokens
    )

    yield

    # Cleanup
    if storage:
        await storage.close()


app = FastAPI(
    title="README Tools API",
    description="API for intelligent README file organization and discovery",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "message": "README Tools API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        database_connected=storage._connection is not None,
    )


@app.post("/api/v1/readme/parse", response_model=ParseResponse)
async def parse_readme(request: ParseReadmeRequest):
    """Parse and index a README file."""
    try:
        # Initialize parser
        parser = Parser()

        # Parse README
        if request.file_path:
            sections = await parser.parse_file(request.file_path)
        elif request.content:
            sections = await parser.parse_content(request.content)
        else:
            raise HTTPException(status_code=400, detail="Either file_path or content required")

        # Initialize AI adapter
        api_key = None
        if request.ai_provider == "openai":
            api_key = settings.openai_api_key
        elif request.ai_provider == "anthropic":
            api_key = settings.anthropic_api_key
        elif request.ai_provider == "openrouter":
            api_key = settings.openrouter_api_key

        ai_adapter = get_ai_adapter(
            provider=request.ai_provider,
            api_key=api_key,
            model=request.model,
        )

        # Initialize categorizer and indexer
        categorizer = Categorizer(ai_adapter, request.custom_categories)
        indexer = Indexer(storage, categorizer)

        # Index README
        stats = await indexer.index_readme(sections, request.custom_categories)

        return ParseResponse(
            success=True,
            message="README parsed and indexed successfully",
            stats=stats,
            sections_indexed=stats["sections_indexed"],
            categories=stats["categories_created"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/readme/parts", response_model=List[ReadmePart])
async def list_parts(limit: int = 100, offset: int = 0):
    """List all README parts."""
    try:
        if not storage._connection:
            raise HTTPException(status_code=500, detail="Database not connected")

        query = """
            SELECT * FROM readme_parts
            ORDER BY order_index
            LIMIT ? OFFSET ?
        """

        cursor = await storage._connection.execute(query, (limit, offset))
        rows = await cursor.fetchall()

        parts = []
        for row in rows:
            keywords = await storage.get_keywords(row["id"])
            tags = await storage.get_tags(row["id"])

            parts.append(
                ReadmePart(
                    id=row["id"],
                    title=row["title"],
                    content=row["content"],
                    category=row["category"],
                    parent_id=row["parent_id"],
                    order_index=row["order_index"],
                    metadata=row["metadata"],
                    keywords=keywords,
                    tags=tags,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )

        return parts

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/readme/parts/{part_id}", response_model=ReadmePart)
async def get_part(part_id: str):
    """Get a specific README part."""
    try:
        part = await storage.get_part(part_id)
        if not part:
            raise HTTPException(status_code=404, detail="Part not found")

        keywords = await storage.get_keywords(part_id)
        tags = await storage.get_tags(part_id)

        return ReadmePart(
            id=part["id"],
            title=part["title"],
            content=part["content"],
            category=part["category"],
            parent_id=part["parent_id"],
            order_index=part["order_index"],
            metadata=part["metadata"],
            keywords=keywords,
            tags=tags,
            created_at=part["created_at"],
            updated_at=part["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Full-text search across README content."""
    try:
        filters = {}
        if request.category:
            filters["category"] = request.category
        if request.tags:
            filters["tags"] = request.tags
        if request.keywords:
            filters["keywords"] = request.keywords

        results = await search_engine.search(
            query=request.query,
            filters=filters if filters else None,
            limit=request.limit,
            offset=request.offset,
        )

        search_results = [
            SearchResult(
                part_id=r["part_id"],
                title=r["title"],
                content=r["content"],
                category=r["category"],
                snippet=r.get("snippet"),
                rank=r.get("rank"),
                keywords=r.get("keywords"),
                tags=r.get("tags"),
            )
            for r in results["results"]
        ]

        return SearchResponse(
            query=results["query"],
            total=results["total"],
            results=search_results,
            limit=results["limit"],
            offset=results["offset"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/search/keywords")
async def search_by_keywords(request: KeywordSearchRequest):
    """Search by keywords."""
    try:
        results = await search_engine.search_by_keywords(request.keywords, request.limit)

        return [
            SearchResult(
                part_id=r["part_id"],
                title=r["title"],
                content=r["content"],
                category=r["category"],
                keywords=r.get("keywords"),
                tags=r.get("tags"),
            )
            for r in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/search/tags")
async def search_by_tags(request: TagSearchRequest):
    """Search by tags."""
    try:
        results = await search_engine.search_by_tags(
            request.tags, match_all=request.match_all, limit=request.limit
        )

        return [
            SearchResult(
                part_id=r["part_id"],
                title=r["title"],
                content=r["content"],
                category=r["category"],
                keywords=r.get("keywords"),
                tags=r.get("tags"),
            )
            for r in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/context/request", response_model=ContextResponse)
async def request_context(request: ContextRequest):
    """Request relevant context for AI agents."""
    try:
        if request.query:
            result = await context_provider.get_context(
                query=request.query,
                max_tokens=request.max_tokens,
                include_related=request.include_related,
            )
        elif request.category:
            result = await context_provider.get_context_by_category(
                category=request.category, max_tokens=request.max_tokens
            )
        elif request.tags:
            result = await context_provider.get_context_by_tags(
                tags=request.tags, max_tokens=request.max_tokens
            )
        else:
            raise HTTPException(
                status_code=400, detail="Either query, category, or tags required"
            )

        sections = [
            ContextSection(
                part_id=s["part_id"],
                title=s["title"],
                content=s["content"],
                tags=s.get("tags"),
            )
            for s in result["sections"]
        ]

        return ContextResponse(
            query=result.get("query"),
            category=result.get("category"),
            tags=result.get("tags"),
            context=result["context"],
            sections=sections,
            token_estimate=result["token_estimate"],
            sections_included=result["sections_included"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/categories")
async def get_categories():
    """Get all categories."""
    try:
        categories = await storage.get_all_categories()
        return categories

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/keywords")
async def get_keywords():
    """Get all keywords with usage counts."""
    try:
        keywords = await search_engine.get_all_keywords()
        return keywords

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tags")
async def get_tags():
    """Get all tags with usage counts."""
    try:
        tags = await search_engine.get_all_tags()
        return tags

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats():
    """Get statistics about indexed content."""
    try:
        summary = await context_provider.get_summary()

        return StatsResponse(
            total_categories=summary["total_categories"],
            categories=summary["categories"],
            total_keywords=summary["total_keywords"],
            top_keywords=summary["top_keywords"],
            total_tags=summary["total_tags"],
            top_tags=summary["top_tags"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404, content=ErrorResponse(error="Not found", detail=str(exc)).dict()
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal server error", detail=str(exc)).dict(),
    )
