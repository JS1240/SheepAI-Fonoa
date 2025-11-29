"""Web scraper service using Bright Data Web Unlocker for The Hacker News."""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)


class ScrapedArticle(BaseModel):
    """Model for freshly scraped article data."""

    url: str
    title: str = ""
    full_content: str = ""
    author: str = Field(default="Unknown")
    published_at: datetime = Field(default_factory=datetime.utcnow)
    tags: list[str] = Field(default_factory=list)
    related_urls: list[str] = Field(default_factory=list)
    thumbnail_url: str = ""
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class ScraperMetrics(BaseModel):
    """Metrics for scraper health monitoring."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_success_time: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


class BrightDataClient:
    """HTTP client configured with Bright Data Web Unlocker proxy."""

    DIRECT_API_URL = "https://api.brightdata.com/request"

    def __init__(self) -> None:
        """Initialize the Bright Data client."""
        self.api_key = settings.brightdata_api_key
        self.zone_name = settings.brightdata_zone_name
        self.timeout = settings.scraping_timeout_seconds
        self.rate_limit_delay = settings.scraping_rate_limit_seconds
        self._last_request_time: Optional[float] = None
        self.metrics = ScraperMetrics()

    def is_configured(self) -> bool:
        """Check if Bright Data credentials are configured."""
        return bool(self.api_key and self.zone_name)

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self._last_request_time is not None:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content through Bright Data Web Unlocker Direct API.

        Args:
            url: The URL to fetch

        Returns:
            HTML content as string, or None if failed
        """
        if not self.is_configured():
            logger.warning("Bright Data not configured, cannot fetch URL: %s", url)
            return None

        await self._apply_rate_limit()
        self.metrics.total_requests += 1

        payload = {
            "zone": self.zone_name,
            "url": url,
            "format": "raw",
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.DIRECT_API_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

                self.metrics.successful_requests += 1
                self.metrics.last_success_time = datetime.utcnow()
                logger.debug("Successfully fetched URL: %s", url)
                return response.text

        except httpx.HTTPStatusError as e:
            self.metrics.failed_requests += 1
            self.metrics.last_error = f"HTTP {e.response.status_code}: {str(e)}"
            self.metrics.last_error_time = datetime.utcnow()
            logger.error("HTTP error fetching %s: %s", url, e)
            raise

        except httpx.RequestError as e:
            self.metrics.failed_requests += 1
            self.metrics.last_error = str(e)
            self.metrics.last_error_time = datetime.utcnow()
            logger.error("Request error fetching %s: %s", url, e)
            raise


class TheHackerNewsParser:
    """HTML parser for The Hacker News website."""

    BASE_URL = "https://thehackernews.com"

    # Homepage selectors
    HOMEPAGE_ARTICLE_SELECTOR = ".body-post"
    HOMEPAGE_LINK_SELECTOR = ".story-link"
    HOMEPAGE_TITLE_SELECTOR = ".home-title"
    HOMEPAGE_DESC_SELECTOR = ".home-desc"
    HOMEPAGE_DATE_SELECTOR = ".item-label"
    HOMEPAGE_THUMBNAIL_SELECTOR = ".home-img img"

    # Article page selectors
    ARTICLE_TITLE_SELECTOR = ".story-title"
    ARTICLE_CONTENT_SELECTOR = ".articlebody"
    ARTICLE_AUTHOR_SELECTORS = [
        ".postmeta .author",           # Primary: standard articles
        ".postmeta span.author",       # Alternative selector
        ".author-name",                # Some pages use this
        'meta[name="author"]',         # Fallback: meta tag
    ]
    ARTICLE_DATE_SELECTOR = ".postmeta"
    ARTICLE_TAGS_SELECTOR = ".m-tags"
    ARTICLE_RELATED_SELECTOR = ".latest-link"
    ARTICLE_OG_IMAGE_SELECTOR = 'meta[property="og:image"]'

    # Pagination selector
    OLDER_POSTS_SELECTOR = ".blog-pager-older-link-mobile"

    def parse_homepage(self, html: str) -> list[dict]:
        """Parse homepage to extract article metadata.

        Args:
            html: HTML content of the homepage

        Returns:
            List of article metadata dicts with url, title, description, date
        """
        soup = BeautifulSoup(html, "lxml")
        articles = []

        for post in soup.select(self.HOMEPAGE_ARTICLE_SELECTOR):
            try:
                link_elem = post.select_one(self.HOMEPAGE_LINK_SELECTOR)
                title_elem = post.select_one(self.HOMEPAGE_TITLE_SELECTOR)
                desc_elem = post.select_one(self.HOMEPAGE_DESC_SELECTOR)
                date_elem = post.select_one(self.HOMEPAGE_DATE_SELECTOR)
                thumb_elem = post.select_one(self.HOMEPAGE_THUMBNAIL_SELECTOR)

                if not link_elem or not title_elem:
                    continue

                url = link_elem.get("href", "")
                if not url.startswith("http"):
                    url = urljoin(self.BASE_URL, url)

                articles.append({
                    "url": url,
                    "title": title_elem.get_text(strip=True),
                    "description": desc_elem.get_text(strip=True) if desc_elem else "",
                    "date_label": date_elem.get_text(strip=True) if date_elem else "",
                    "thumbnail_url": thumb_elem.get("src", "") if thumb_elem else "",
                })

            except Exception as e:
                logger.warning("Error parsing homepage article: %s", e)
                continue

        logger.info("Parsed %d articles from homepage", len(articles))
        return articles

    def get_next_page_url(self, html: str) -> Optional[str]:
        """Extract the 'Older Posts' pagination URL.

        Args:
            html: HTML content of the current page

        Returns:
            URL of the next page, or None if not found
        """
        soup = BeautifulSoup(html, "lxml")
        older_link = soup.select_one(self.OLDER_POSTS_SELECTOR)

        if older_link and older_link.get("href"):
            url = older_link.get("href")
            if not url.startswith("http"):
                url = urljoin(self.BASE_URL, url)
            return url

        return None

    def parse_article(self, html: str, url: str) -> ScrapedArticle:
        """Parse a full article page.

        Args:
            html: HTML content of the article page
            url: URL of the article

        Returns:
            ScrapedArticle with extracted data
        """
        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title_elem = soup.select_one(self.ARTICLE_TITLE_SELECTOR)
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract full content
        content_elem = soup.select_one(self.ARTICLE_CONTENT_SELECTOR)
        full_content = ""
        if content_elem:
            # Remove script and style elements
            for script in content_elem.select("script, style, .adsbygoogle"):
                script.decompose()
            full_content = content_elem.get_text(separator="\n", strip=True)

        # Extract author with fallback selectors
        author = "Unknown"
        for selector in self.ARTICLE_AUTHOR_SELECTORS:
            author_elem = soup.select_one(selector)
            if author_elem:
                if selector.startswith('meta'):
                    author = author_elem.get("content", "").strip()
                else:
                    author = author_elem.get_text(strip=True)
                if author:
                    author = author.replace("by ", "").replace("By ", "").strip()
                    # Validate author is not a date
                    if not self._looks_like_date(author):
                        break
                    else:
                        author = "Unknown"  # Reset if it looks like a date

        # Extract date
        date_elem = soup.select_one(self.ARTICLE_DATE_SELECTOR)
        published_at = datetime.utcnow()
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            published_at = self._parse_date(date_text)

        # Extract tags from m-tags
        tags = []
        tags_elem = soup.select_one(self.ARTICLE_TAGS_SELECTOR)
        if tags_elem:
            # Tags are often in format "Category / Tag1 / Tag2"
            tags_text = tags_elem.get_text(strip=True)
            tags = [t.strip() for t in tags_text.split("/") if t.strip()]

        # Extract related article URLs
        related_urls = []
        for related in soup.select(self.ARTICLE_RELATED_SELECTOR):
            href = related.get("href", "")
            if href and "thehackernews.com" in href:
                related_urls.append(href)

        # Extract thumbnail from og:image
        thumbnail_url = ""
        og_image = soup.select_one(self.ARTICLE_OG_IMAGE_SELECTOR)
        if og_image and og_image.get("content"):
            thumbnail_url = og_image.get("content")

        return ScrapedArticle(
            url=url,
            title=title,
            full_content=full_content,
            author=author,
            published_at=published_at,
            tags=tags,
            related_urls=related_urls[:5],  # Limit to 5 related
            thumbnail_url=thumbnail_url,
            scraped_at=datetime.utcnow(),
        )

    def _parse_date(self, date_text: str) -> datetime:
        """Parse date from article metadata.

        Args:
            date_text: Date text from the article

        Returns:
            Parsed datetime, or current time if parsing fails
        """
        try:
            # Common format: "Nov 28, 2025"
            # Also handles: "Thursday, November 28, 2025"
            # Extract just the date portion using regex
            date_match = re.search(
                r'([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})',
                date_text
            )
            if date_match:
                return dateparser.parse(date_match.group(1))

            # Try parsing the whole text
            return dateparser.parse(date_text)

        except Exception as e:
            logger.warning("Could not parse date '%s': %s", date_text, e)
            return datetime.utcnow()

    def _looks_like_date(self, text: str) -> bool:
        """Check if text looks like a date rather than an author name.

        Args:
            text: Text to check

        Returns:
            True if text appears to be a date string
        """
        if not text:
            return False
        date_patterns = [
            r'^[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}$',  # "Nov 17, 2025"
            r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',       # "11/17/2025"
            r'^[A-Za-z]+day,?\s+[A-Za-z]+\s+\d{1,2}',  # "Thursday, November 28"
        ]
        return any(re.match(pattern, text.strip()) for pattern in date_patterns)


class ScraperService:
    """Main scraper service with rate limiting and batch processing."""

    def __init__(self) -> None:
        """Initialize the scraper service."""
        self.client = BrightDataClient()
        self.parser = TheHackerNewsParser()
        self.concurrency = settings.scraping_concurrency

    @property
    def metrics(self) -> ScraperMetrics:
        """Get scraper metrics."""
        return self.client.metrics

    def is_configured(self) -> bool:
        """Check if scraper is properly configured."""
        return self.client.is_configured() and settings.scraping_enabled

    async def scrape_homepage(self) -> list[dict]:
        """Scrape the homepage for latest article URLs.

        Returns:
            List of article metadata dicts
        """
        if not self.is_configured():
            logger.warning("Scraper not configured, returning empty list")
            return []

        html = await self.client.fetch_url(self.parser.BASE_URL)
        if not html:
            return []

        return self.parser.parse_homepage(html)

    async def scrape_article(self, url: str) -> Optional[ScrapedArticle]:
        """Scrape a single article page.

        Args:
            url: URL of the article to scrape

        Returns:
            ScrapedArticle or None if failed or invalid
        """
        if not self.is_configured():
            logger.warning("Scraper not configured, cannot scrape article")
            return None

        html = await self.client.fetch_url(url)
        if not html:
            return None

        try:
            article = self.parser.parse_article(html, url)
            # Validate required fields
            if not article.title or len(article.title.strip()) == 0:
                logger.warning("Skipping article with empty title: %s", url)
                return None
            if not article.full_content or len(article.full_content.strip()) < 100:
                logger.warning("Skipping article with insufficient content: %s", url)
                return None
            return article
        except Exception as e:
            logger.error("Error parsing article %s: %s", url, e)
            return None

    async def scrape_articles_batch(
        self,
        urls: list[str],
        concurrency: Optional[int] = None,
    ) -> list[ScrapedArticle]:
        """Scrape multiple articles with controlled concurrency.

        Args:
            urls: List of article URLs to scrape
            concurrency: Max concurrent requests (default from settings)

        Returns:
            List of successfully scraped articles
        """
        if not urls:
            return []

        concurrency = concurrency or self.concurrency
        semaphore = asyncio.Semaphore(concurrency)
        results: list[ScrapedArticle] = []

        async def scrape_with_semaphore(url: str) -> Optional[ScrapedArticle]:
            async with semaphore:
                return await self.scrape_article(url)

        tasks = [scrape_with_semaphore(url) for url in urls]
        scraped_items = await asyncio.gather(*tasks, return_exceptions=True)

        for item in scraped_items:
            if isinstance(item, ScrapedArticle):
                results.append(item)
            elif isinstance(item, Exception):
                logger.error("Batch scrape error: %s", item)

        logger.info("Batch scraped %d/%d articles", len(results), len(urls))
        return results

    async def scrape_archive(
        self,
        days_back: int = 30,
        max_articles: Optional[int] = None,
    ) -> list[ScrapedArticle]:
        """Scrape historical articles from the archive.

        Args:
            days_back: How many days of history to scrape
            max_articles: Maximum number of articles to scrape

        Returns:
            List of scraped articles
        """
        if not self.is_configured():
            logger.warning("Scraper not configured, cannot scrape archive")
            return []

        max_articles = max_articles or settings.archive_max_articles
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        all_article_urls: list[str] = []

        # Start from homepage
        current_url = self.parser.BASE_URL
        pages_scraped = 0
        max_pages = 50  # Safety limit

        logger.info("Starting archive scrape: %d days back, max %d articles", days_back, max_articles)

        while current_url and pages_scraped < max_pages:
            html = await self.client.fetch_url(current_url)
            if not html:
                break

            articles = self.parser.parse_homepage(html)
            if not articles:
                break

            # Check if we've gone past the cutoff date
            # Parse the last article's date to check
            last_article = articles[-1]
            if last_article.get("date_label"):
                try:
                    last_date = dateparser.parse(last_article["date_label"])
                    if last_date and last_date < cutoff_date:
                        logger.info("Reached cutoff date, stopping archive scrape")
                        # Still add articles from this page that are within date range
                        for article in articles:
                            if len(all_article_urls) >= max_articles:
                                break
                            all_article_urls.append(article["url"])
                        break
                except Exception:
                    pass

            # Add article URLs
            for article in articles:
                if len(all_article_urls) >= max_articles:
                    break
                all_article_urls.append(article["url"])

            if len(all_article_urls) >= max_articles:
                break

            # Get next page URL
            current_url = self.parser.get_next_page_url(html)
            pages_scraped += 1

            logger.info("Archive progress: %d articles found, page %d", len(all_article_urls), pages_scraped)

        logger.info("Found %d article URLs in archive", len(all_article_urls))

        # Scrape all articles in batches
        return await self.scrape_articles_batch(all_article_urls)


# Global service instance
scraper_service = ScraperService()
