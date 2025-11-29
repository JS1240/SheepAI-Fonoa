"""Article data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ArticleBase(BaseModel):
    """Base article fields."""

    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=1)
    content: str = Field(default="")
    summary: Optional[str] = Field(default=None, max_length=1000)
    published_at: datetime

    # Scraper-enhanced fields
    author: str = Field(default="Unknown")
    tags: list[str] = Field(default_factory=list)
    thumbnail_url: str = Field(default="")
    source: str = Field(default="rss", description="Data source: 'rss' or 'scraped'")


class ArticleCreate(ArticleBase):
    """Model for creating a new article."""

    pass


class Article(ArticleBase):
    """Full article model with intelligence fields."""

    id: str = Field(..., description="Unique article identifier")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    # Intelligence fields
    embedding: Optional[list[float]] = Field(default=None)
    entities: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    threat_actors: list[str] = Field(default_factory=list)
    vulnerabilities: list[str] = Field(default_factory=list)

    # Story tracking
    story_id: Optional[str] = Field(default=None, description="ID of the story thread")

    # Graph connections
    related_article_ids: list[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "thn-2025-001",
                "title": "Critical RCE Vulnerability Discovered in Apache Struts",
                "url": "https://thehackernews.com/2025/01/apache-struts-rce.html",
                "content": "Security researchers have discovered...",
                "summary": "A critical remote code execution vulnerability affects Apache Struts versions 2.x",
                "published_at": "2025-01-15T10:30:00Z",
                "scraped_at": "2025-01-15T10:45:00Z",
                "author": "Ravie Lakshmanan",
                "tags": ["Vulnerability", "Apache"],
                "thumbnail_url": "https://thehackernews.com/images/apache-struts.jpg",
                "source": "scraped",
                "categories": ["vulnerability", "apache", "rce"],
                "vulnerabilities": ["CVE-2025-1234"],
                "related_article_ids": ["thn-2025-002", "thn-2024-998"],
            }
        }


class ArticleSummary(BaseModel):
    """Lightweight article representation for lists."""

    id: str
    title: str
    url: str
    summary: Optional[str] = None
    published_at: datetime
    categories: list[str] = Field(default_factory=list)
    severity: Optional[str] = Field(default=None, description="critical/high/medium/low")
