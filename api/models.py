"""Pydantic models for API requests and responses."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Request Models

class ParseReadmeRequest(BaseModel):
    """Request to parse a README file."""

    file_path: Optional[str] = Field(None, description="Path to README file")
    content: Optional[str] = Field(None, description="README content as string")
    ai_provider: str = Field("openai", description="AI provider to use")
    model: Optional[str] = Field(None, description="Model name (optional)")
    custom_categories: Optional[List[str]] = Field(None, description="Custom categories")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "README.md",
                "ai_provider": "openai",
                "model": "gpt-4-turbo",
            }
        }


class SearchRequest(BaseModel):
    """Search request."""

    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    keywords: Optional[List[str]] = Field(None, description="Filter by keywords")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "installation setup",
                "limit": 10,
            }
        }


class ContextRequest(BaseModel):
    """Context request for AI agents."""

    query: Optional[str] = Field(None, description="Query or topic")
    category: Optional[str] = Field(None, description="Specific category")
    tags: Optional[List[str]] = Field(None, description="Specific tags")
    max_tokens: int = Field(4000, ge=100, le=16000, description="Maximum tokens")
    include_related: bool = Field(True, description="Include related sections")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "How do I configure the database?",
                "max_tokens": 2000,
                "include_related": True,
            }
        }


class KeywordSearchRequest(BaseModel):
    """Keyword search request."""

    keywords: List[str] = Field(..., description="Keywords to search")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")


class TagSearchRequest(BaseModel):
    """Tag search request."""

    tags: List[str] = Field(..., description="Tags to search")
    match_all: bool = Field(False, description="Require all tags")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")


# Response Models

class ParseResponse(BaseModel):
    """Parse response."""

    success: bool
    message: str
    stats: Optional[Dict[str, Any]] = None
    sections_indexed: Optional[int] = None
    categories: Optional[List[str]] = None


class SearchResult(BaseModel):
    """Single search result."""

    part_id: str
    title: str
    content: str
    category: str
    snippet: Optional[str] = None
    rank: Optional[float] = None
    keywords: Optional[Dict[str, float]] = None
    tags: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search response."""

    query: str
    total: int
    results: List[SearchResult]
    limit: int
    offset: int


class ReadmePart(BaseModel):
    """README part details."""

    id: str
    title: str
    content: str
    category: str
    parent_id: Optional[str] = None
    order_index: int
    metadata: Optional[Dict[str, Any]] = None
    keywords: Optional[Dict[str, float]] = None
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ContextSection(BaseModel):
    """Context section for AI agents."""

    part_id: str
    title: str
    content: str
    tags: Optional[List[str]] = None


class ContextResponse(BaseModel):
    """Context response for AI agents."""

    query: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    context: str = Field(..., description="Formatted context string")
    sections: List[ContextSection]
    token_estimate: int
    sections_included: int


class Category(BaseModel):
    """Category model."""

    id: str
    name: str
    description: Optional[str] = None
    parent_category: Optional[str] = None


class StatsResponse(BaseModel):
    """Statistics response."""

    total_categories: int
    categories: List[str]
    total_keywords: int
    top_keywords: Dict[str, int]
    total_tags: int
    top_tags: Dict[str, int]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database_connected: bool


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: Optional[str] = None
