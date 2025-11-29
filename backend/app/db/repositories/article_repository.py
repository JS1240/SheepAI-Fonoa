"""Article repository for Supabase database operations."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from supabase import Client

from app.db.supabase_client import get_supabase_client
from app.models.article import Article, ArticleSummary

logger = logging.getLogger(__name__)


class ArticleRepository:
    """Repository for article CRUD operations and vector similarity search."""

    def __init__(self, client: Optional[Client] = None):
        """Initialize the repository with a Supabase client."""
        self._client = client

    @property
    def client(self) -> Client:
        """Get the Supabase client (lazy initialization)."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def create(self, article: Article) -> Article:
        """Create a new article in the database."""
        data = {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "content": article.content,
            "summary": article.summary,
            "embedding": article.embedding,
            "categories": article.categories,
            "vulnerabilities": article.vulnerabilities,
            "threat_actors": article.threat_actors,
            "story_id": article.story_id,
            "related_article_ids": article.related_article_ids,
            "published_at": article.published_at.isoformat(),
            "scraped_at": article.scraped_at.isoformat(),
            # Scraper-enhanced fields
            "author": article.author,
            "tags": article.tags,
            "thumbnail_url": article.thumbnail_url,
            "source": article.source,
        }

        try:
            result = self.client.table("articles").insert(data).execute()
            logger.info("Created article: %s", article.id)
            return article
        except Exception as e:
            logger.error("Failed to create article %s: %s", article.id, str(e))
            raise

    async def get_by_id(self, article_id: str) -> Optional[Article]:
        """Get an article by its ID."""
        try:
            result = (
                self.client.table("articles")
                .select("*")
                .eq("id", article_id)
                .single()
                .execute()
            )

            if result.data:
                return self._row_to_article(result.data)
            return None
        except Exception as e:
            logger.error("Failed to get article %s: %s", article_id, str(e))
            return None

    async def get_by_url(self, url: str) -> Optional[Article]:
        """Get an article by its URL."""
        try:
            result = (
                self.client.table("articles")
                .select("*")
                .eq("url", url)
                .single()
                .execute()
            )

            if result.data:
                return self._row_to_article(result.data)
            return None
        except Exception as e:
            logger.debug("Article not found for URL %s: %s", url, str(e))
            return None

    async def exists(self, article_id: str) -> bool:
        """Check if an article exists by ID."""
        try:
            result = (
                self.client.table("articles")
                .select("id")
                .eq("id", article_id)
                .single()
                .execute()
            )
            return result.data is not None
        except Exception:
            return False

    async def exists_by_url(self, url: str) -> bool:
        """Check if an article exists by URL."""
        try:
            result = (
                self.client.table("articles")
                .select("id")
                .eq("url", url)
                .single()
                .execute()
            )
            return result.data is not None
        except Exception:
            return False

    async def update(self, article: Article) -> Article:
        """Update an existing article."""
        # Core fields that always exist in the database
        data = {
            "title": article.title,
            "content": article.content,
            "summary": article.summary,
            "embedding": article.embedding,
            "categories": article.categories,
            "vulnerabilities": article.vulnerabilities,
            "threat_actors": article.threat_actors,
            "story_id": article.story_id,
            "related_article_ids": article.related_article_ids,
            "updated_at": datetime.utcnow().isoformat(),
        }
        # Note: Scraper-enhanced fields (author, tags, thumbnail_url, source)
        # are added via migration 10. If migration hasn't been applied,
        # these columns won't exist. Update them only during create operations.

        try:
            result = (
                self.client.table("articles")
                .update(data)
                .eq("id", article.id)
                .execute()
            )
            logger.info("Updated article: %s", article.id)
            return article
        except Exception as e:
            logger.error("Failed to update article %s: %s", article.id, str(e))
            raise

    async def get_all(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "published_at",
        descending: bool = True,
    ) -> list[Article]:
        """Get all articles with pagination."""
        try:
            query = self.client.table("articles").select("*")

            if descending:
                query = query.order(order_by, desc=True)
            else:
                query = query.order(order_by)

            result = query.range(offset, offset + limit - 1).execute()

            return [self._row_to_article(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get articles: %s", str(e))
            return []

    async def get_summaries(
        self,
        limit: int = 50,
        offset: int = 0,
        categories: Optional[list[str]] = None,
        days: Optional[int] = None,
    ) -> list[ArticleSummary]:
        """Get article summaries for listing."""
        try:
            query = self.client.table("articles").select(
                "id, title, url, summary, published_at, categories"
            )

            if days:
                cutoff = datetime.utcnow() - timedelta(days=days)
                query = query.gte("published_at", cutoff.isoformat())

            if categories:
                query = query.overlaps("categories", categories)

            result = (
                query.order("published_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            return [
                ArticleSummary(
                    id=row["id"],
                    title=row["title"],
                    url=row["url"],
                    summary=row.get("summary"),
                    published_at=datetime.fromisoformat(
                        row["published_at"].replace("Z", "+00:00")
                    ),
                    categories=row.get("categories", []),
                )
                for row in result.data
            ]
        except Exception as e:
            logger.error("Failed to get article summaries: %s", str(e))
            return []

    async def search(
        self,
        query: Optional[str] = None,
        categories: Optional[list[str]] = None,
        days: Optional[int] = None,
        limit: int = 20,
    ) -> list[ArticleSummary]:
        """Search articles by text and filters."""
        try:
            db_query = self.client.table("articles").select(
                "id, title, url, summary, published_at, categories"
            )

            if days:
                cutoff = datetime.utcnow() - timedelta(days=days)
                db_query = db_query.gte("published_at", cutoff.isoformat())

            if categories:
                db_query = db_query.overlaps("categories", categories)

            if query:
                db_query = db_query.or_(
                    f"title.ilike.%{query}%,summary.ilike.%{query}%,content.ilike.%{query}%"
                )

            result = (
                db_query.order("published_at", desc=True).limit(limit).execute()
            )

            return [
                ArticleSummary(
                    id=row["id"],
                    title=row["title"],
                    url=row["url"],
                    summary=row.get("summary"),
                    published_at=datetime.fromisoformat(
                        row["published_at"].replace("Z", "+00:00")
                    ),
                    categories=row.get("categories", []),
                )
                for row in result.data
            ]
        except Exception as e:
            logger.error("Failed to search articles: %s", str(e))
            return []

    async def find_similar(
        self,
        embedding: list[float],
        threshold: float = 0.75,
        limit: int = 5,
        exclude_ids: Optional[list[str]] = None,
    ) -> list[tuple[ArticleSummary, float]]:
        """Find similar articles using vector similarity search."""
        try:
            result = self.client.rpc(
                "match_articles",
                {
                    "query_embedding": embedding,
                    "match_threshold": threshold,
                    "match_count": limit + len(exclude_ids or []),
                },
            ).execute()

            similar = []
            for row in result.data:
                if exclude_ids and row["id"] in exclude_ids:
                    continue

                summary = ArticleSummary(
                    id=row["id"],
                    title=row["title"],
                    url=row["url"],
                    summary=row.get("summary"),
                    published_at=datetime.fromisoformat(
                        row["published_at"].replace("Z", "+00:00")
                    ),
                    categories=row.get("categories", []),
                )
                similar.append((summary, row["similarity"]))

                if len(similar) >= limit:
                    break

            return similar
        except Exception as e:
            logger.error("Failed to find similar articles: %s", str(e))
            return []

    async def get_count(self) -> int:
        """Get total count of articles."""
        try:
            result = (
                self.client.table("articles")
                .select("id", count="exact")
                .execute()
            )
            return result.count or 0
        except Exception as e:
            logger.error("Failed to get article count: %s", str(e))
            return 0

    async def get_recent_ids(self, days: int = 30) -> list[str]:
        """Get IDs of recent articles."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = (
                self.client.table("articles")
                .select("id")
                .gte("published_at", cutoff.isoformat())
                .execute()
            )
            return [row["id"] for row in result.data]
        except Exception as e:
            logger.error("Failed to get recent article IDs: %s", str(e))
            return []

    def _row_to_article(self, row: dict) -> Article:
        """Convert a database row to an Article model."""
        # Parse embedding from string if needed (Supabase returns vector as string)
        embedding = row.get("embedding")
        if embedding and isinstance(embedding, str):
            import json
            try:
                embedding = json.loads(embedding)
            except (json.JSONDecodeError, TypeError):
                embedding = None

        return Article(
            id=row["id"],
            title=row["title"],
            url=row["url"],
            content=row.get("content", ""),
            summary=row.get("summary"),
            embedding=embedding,
            categories=row.get("categories", []),
            vulnerabilities=row.get("vulnerabilities", []),
            threat_actors=row.get("threat_actors", []),
            story_id=row.get("story_id"),
            related_article_ids=row.get("related_article_ids", []),
            published_at=datetime.fromisoformat(
                row["published_at"].replace("Z", "+00:00")
            ),
            scraped_at=datetime.fromisoformat(
                row["scraped_at"].replace("Z", "+00:00")
            ),
            # Scraper-enhanced fields
            author=row.get("author", "Unknown"),
            tags=row.get("tags", []),
            thumbnail_url=row.get("thumbnail_url", ""),
            source=row.get("source", "rss"),
        )
