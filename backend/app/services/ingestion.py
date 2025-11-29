"""RSS feed ingestion service for The Hacker News with optional Bright Data scraping."""

import hashlib
import logging
from datetime import datetime
from typing import Optional

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.db.repositories import ArticleRepository
from app.models.article import Article, ArticleCreate
from app.services.scraper import ScrapedArticle, scraper_service

_notification_service = None


def _get_notification_service():
    """Lazy import to avoid circular imports."""
    global _notification_service
    if _notification_service is None:
        from app.services.notification import notification_service
        _notification_service = notification_service
    return _notification_service

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting articles from RSS feeds with optional Bright Data scraping.

    Supports three ingestion modes:
    1. RSS-only: Fast discovery with summary content (fallback mode)
    2. Hybrid: RSS discovery + Bright Data scraping for full content (recommended)
    3. Archive: Historical scraping with pagination for backfill
    """

    def __init__(self, article_repo: Optional[ArticleRepository] = None) -> None:
        self.rss_url = settings.hackernews_rss_url
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self._articles_cache: dict[str, Article] = {}
        self._article_repo = article_repo or ArticleRepository()
        self._scraper = scraper_service

    async def fetch_rss_feed(self) -> list[dict]:
        """Fetch and parse the RSS feed."""
        try:
            response = await self.http_client.get(self.rss_url)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

            if feed.bozo:
                logger.warning("RSS feed parsing had issues: %s", feed.bozo_exception)

            return feed.entries
        except httpx.HTTPError as e:
            logger.error("Failed to fetch RSS feed: %s", e)
            return []

    def _generate_article_id(self, url: str) -> str:
        """Generate a unique article ID from URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"thn-{url_hash}"

    def _parse_published_date(self, entry: dict) -> datetime:
        """Parse the published date from an RSS entry."""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        return datetime.utcnow()

    def _extract_content(self, entry: dict) -> str:
        """Extract article content from RSS entry."""
        content = ""

        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary
        elif hasattr(entry, "description"):
            content = entry.description

        # Clean HTML
        if content:
            soup = BeautifulSoup(content, "lxml")
            content = soup.get_text(separator=" ", strip=True)

        return content

    def _scraped_to_article(self, scraped: ScrapedArticle) -> Article:
        """Convert a ScrapedArticle to an Article model."""
        article_id = self._generate_article_id(scraped.url)
        return Article(
            id=article_id,
            title=scraped.title,
            url=scraped.url,
            content=scraped.full_content,
            published_at=scraped.published_at,
            scraped_at=scraped.scraped_at,
            author=scraped.author,
            tags=scraped.tags,
            thumbnail_url=scraped.thumbnail_url,
            source="scraped",
        )

    def is_scraper_configured(self) -> bool:
        """Check if Bright Data scraper is properly configured and enabled."""
        return self._scraper.is_configured()

    async def parse_entry_to_article(self, entry: dict) -> Optional[ArticleCreate]:
        """Parse an RSS entry into an ArticleCreate model."""
        try:
            url = entry.get("link", "")
            if not url:
                return None

            title = entry.get("title", "Untitled")
            content = self._extract_content(entry)
            published_at = self._parse_published_date(entry)

            return ArticleCreate(
                title=title,
                url=url,
                content=content,
                published_at=published_at,
            )
        except Exception as e:
            logger.error("Failed to parse RSS entry: %s", e)
            return None

    async def ingest_articles(self, use_scraper: bool = True) -> list[Article]:
        """Fetch RSS feed and create Article objects.

        Args:
            use_scraper: If True and scraper is configured, fetch full content via Bright Data.
                        If False or scraper not configured, use RSS content only.

        Returns:
            List of newly ingested articles.
        """
        entries = await self.fetch_rss_feed()
        articles: list[Article] = []
        urls_to_scrape: list[str] = []

        # First pass: collect new article URLs
        for entry in entries[: settings.max_articles_per_fetch]:
            article_create = await self.parse_entry_to_article(entry)
            if not article_create:
                continue

            article_id = self._generate_article_id(article_create.url)

            # Skip if already in cache or database
            if article_id in self._articles_cache:
                continue
            if await self._article_repo.exists(article_id):
                logger.debug("Article already exists in DB: %s", article_id)
                continue

            urls_to_scrape.append(article_create.url)

        if not urls_to_scrape:
            logger.info("No new articles to ingest")
            return articles

        # Decide ingestion mode
        should_scrape = use_scraper and self.is_scraper_configured()

        if should_scrape:
            # Hybrid mode: scrape full content
            logger.info("Using Bright Data scraper for %d articles", len(urls_to_scrape))
            scraped_articles = await self._scraper.scrape_articles_batch(urls_to_scrape)

            for scraped in scraped_articles:
                try:
                    article = self._scraped_to_article(scraped)
                except Exception as e:
                    logger.warning("Failed to convert scraped article: %s - %s", scraped.url, e)
                    continue

                try:
                    await self._article_repo.create(article)
                    self._articles_cache[article.id] = article
                    articles.append(article)
                    logger.info("Ingested (scraped): %s", article.title[:50])
                except Exception as e:
                    logger.warning("Failed to save scraped article to DB: %s", e)

        else:
            # RSS-only mode: use summary content
            logger.info("Using RSS-only mode for %d articles", len(urls_to_scrape))
            for entry in entries[: settings.max_articles_per_fetch]:
                article_create = await self.parse_entry_to_article(entry)
                if not article_create or article_create.url not in urls_to_scrape:
                    continue

                article_id = self._generate_article_id(article_create.url)
                article = Article(
                    id=article_id,
                    title=article_create.title,
                    url=article_create.url,
                    content=article_create.content,
                    published_at=article_create.published_at,
                    scraped_at=datetime.utcnow(),
                    source="rss",
                )

                try:
                    await self._article_repo.create(article)
                    self._articles_cache[article_id] = article
                    articles.append(article)
                    logger.info("Ingested (RSS): %s", article.title[:50])
                except Exception as e:
                    logger.warning("Failed to save article to DB: %s", e)

        logger.info("Ingested %d new articles", len(articles))
        return articles

    async def get_article_by_id(self, article_id: str) -> Optional[Article]:
        """Get an article by ID from cache or database."""
        # Check cache first
        if article_id in self._articles_cache:
            return self._articles_cache[article_id]

        # Try database
        article = await self._article_repo.get_by_id(article_id)
        if article:
            self._articles_cache[article_id] = article
        return article

    async def get_all_articles(self, limit: int = 100) -> list[Article]:
        """Get all articles from database."""
        return await self._article_repo.get_all(limit=limit)

    async def update_article(self, article: Article) -> Article:
        """Update an article in cache and database."""
        self._articles_cache[article.id] = article
        return await self._article_repo.update(article)

    async def load_from_database(self, limit: int = 100) -> int:
        """Load articles from database into cache."""
        articles = await self._article_repo.get_all(limit=limit)
        for article in articles:
            self._articles_cache[article.id] = article
        logger.info("Loaded %d articles from database", len(articles))
        return len(articles)

    async def search_articles(
        self,
        query: Optional[str] = None,
        categories: Optional[list[str]] = None,
        days: int = 30,
        limit: int = 50,
    ) -> list[Article]:
        """Search articles with filters using database."""
        summaries = await self._article_repo.search(
            query=query,
            categories=categories,
            days=days,
            limit=limit,
        )

        # Get full articles for the summaries
        articles = []
        for summary in summaries:
            article = await self.get_article_by_id(summary.id)
            if article:
                articles.append(article)

        return articles

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()

    async def backfill_archive(
        self,
        days_back: int = 30,
        max_articles: Optional[int] = None,
    ) -> list[Article]:
        """Backfill historical articles from The Hacker News archive.

        Uses Bright Data scraper to fetch articles from archive pages.
        Only fetches articles that don't already exist in the database.

        Args:
            days_back: How many days of history to scrape (default: 30)
            max_articles: Maximum number of articles to scrape (default from settings)

        Returns:
            List of newly backfilled articles.
        """
        if not self.is_scraper_configured():
            logger.warning("Cannot backfill: Bright Data scraper not configured")
            return []

        max_articles = max_articles or settings.archive_max_articles
        logger.info("Starting archive backfill: %d days back, max %d articles", days_back, max_articles)

        # Get scraped articles from archive
        scraped_articles = await self._scraper.scrape_archive(
            days_back=days_back,
            max_articles=max_articles,
        )

        articles: list[Article] = []
        skipped = 0

        for scraped in scraped_articles:
            try:
                article = self._scraped_to_article(scraped)
            except Exception as e:
                logger.warning("Failed to convert scraped article: %s - %s", scraped.url, e)
                continue

            # Skip if already exists
            if article.id in self._articles_cache or await self._article_repo.exists(article.id):
                skipped += 1
                continue

            try:
                await self._article_repo.create(article)
                self._articles_cache[article.id] = article
                articles.append(article)
                logger.debug("Backfilled: %s", article.title[:50])
            except Exception as e:
                logger.warning("Failed to save backfill article to DB: %s", e)

        logger.info(
            "Backfill complete: %d new articles, %d skipped (already exist)",
            len(articles),
            skipped,
        )
        return articles

    async def enhance_rss_article(self, article_id: str) -> Optional[Article]:
        """Enhance an existing RSS-ingested article with full scraped content.

        Args:
            article_id: The ID of the article to enhance.

        Returns:
            The enhanced article, or None if enhancement failed.
        """
        if not self.is_scraper_configured():
            logger.warning("Cannot enhance: Bright Data scraper not configured")
            return None

        article = await self.get_article_by_id(article_id)
        if not article:
            logger.warning("Article not found: %s", article_id)
            return None

        if article.source == "scraped":
            logger.debug("Article already scraped: %s", article_id)
            return article

        # Scrape full content
        scraped = await self._scraper.scrape_article(article.url)
        if not scraped:
            logger.warning("Failed to scrape article: %s", article.url)
            return None

        # Update article with scraped content
        article.content = scraped.full_content
        article.author = scraped.author
        article.tags = scraped.tags
        article.thumbnail_url = scraped.thumbnail_url
        article.source = "scraped"

        try:
            await self._article_repo.update(article)
            self._articles_cache[article.id] = article
            logger.info("Enhanced article: %s", article.title[:50])
            return article
        except Exception as e:
            logger.error("Failed to update enhanced article: %s", e)
            return None

    async def enhance_all_rss_articles(self, limit: int = 50) -> int:
        """Enhance all RSS-only articles with full scraped content.

        Args:
            limit: Maximum number of articles to enhance.

        Returns:
            Number of articles successfully enhanced.
        """
        if not self.is_scraper_configured():
            logger.warning("Cannot enhance: Bright Data scraper not configured")
            return 0

        # Get RSS-only articles from database
        all_articles = await self._article_repo.get_all(limit=limit * 2)
        rss_articles = [a for a in all_articles if a.source == "rss"][:limit]

        if not rss_articles:
            logger.info("No RSS-only articles to enhance")
            return 0

        logger.info("Enhancing %d RSS-only articles", len(rss_articles))
        enhanced_count = 0

        for article in rss_articles:
            result = await self.enhance_rss_article(article.id)
            if result:
                enhanced_count += 1

        logger.info("Enhanced %d/%d articles", enhanced_count, len(rss_articles))
        return enhanced_count

    def get_scraper_metrics(self) -> dict:
        """Get current scraper health metrics.

        Returns:
            Dictionary with scraper metrics including success rate, last errors, etc.
        """
        if not self.is_scraper_configured():
            return {"configured": False, "enabled": False}

        metrics = self._scraper.metrics
        return {
            "configured": True,
            "enabled": settings.scraping_enabled,
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
            "success_rate": metrics.success_rate,
            "last_success_time": metrics.last_success_time.isoformat() if metrics.last_success_time else None,
            "last_error": metrics.last_error,
            "last_error_time": metrics.last_error_time.isoformat() if metrics.last_error_time else None,
        }

    async def should_backfill(self) -> bool:
        """Check if database is empty and backfill should be triggered.

        Returns:
            True if database is empty and scraper is configured.
        """
        if not self.is_scraper_configured():
            return False

        count = await self._article_repo.get_count()
        return count == 0


# Singleton instance
ingestion_service = IngestionService()
