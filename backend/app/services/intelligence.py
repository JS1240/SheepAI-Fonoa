"""Intelligence service for embeddings, NLP, and article processing."""

import logging
import re
from typing import Optional

import numpy as np
from openai import AsyncOpenAI

from app.config import settings
from app.db.repositories import ArticleRepository
from app.models.article import Article, ArticleSummary

logger = logging.getLogger(__name__)


class IntelligenceService:
    """Service for AI-powered article intelligence."""

    def __init__(self, article_repo: Optional[ArticleRepository] = None) -> None:
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.embedding_model = settings.embedding_model
        self.llm_model = settings.openai_model
        self._embeddings_cache: dict[str, list[float]] = {}
        self._article_repo = article_repo or ArticleRepository()

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        if not text:
            return []

        # Check cache
        cache_key = text[:500]
        if cache_key in self._embeddings_cache:
            return self._embeddings_cache[cache_key]

        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text[:8000],
            )
            embedding = response.data[0].embedding
            self._embeddings_cache[cache_key] = embedding
            return embedding
        except Exception as e:
            logger.error("Failed to generate embedding: %s", e)
            return []

    async def generate_summary(self, article: Article) -> str:
        """Generate a concise summary of an article."""
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a cybersecurity analyst. Summarize the following "
                            "security news article in 2-3 sentences. Focus on: what "
                            "happened, what's affected, and the severity."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Title: {article.title}\n\nContent: {article.content[:3000]}",
                    },
                ],
                max_completion_tokens=150,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Failed to generate summary: %s", e)
            return ""

    async def extract_entities(self, article: Article) -> dict[str, list[str]]:
        """Extract security-relevant entities from article."""
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract security entities from this article. Return a JSON "
                            "object with these keys: categories (e.g., ransomware, vulnerability, "
                            "breach), vulnerabilities (CVE IDs), threat_actors (group names), "
                            "products (affected software/hardware). Only include entities "
                            "explicitly mentioned. Return valid JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Title: {article.title}\n\nContent: {article.content[:3000]}",
                    },
                ],
                max_completion_tokens=300,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            import json

            result = json.loads(response.choices[0].message.content)
            return {
                "categories": result.get("categories", []),
                "vulnerabilities": result.get("vulnerabilities", []),
                "threat_actors": result.get("threat_actors", []),
                "products": result.get("products", []),
            }
        except Exception as e:
            logger.error("Failed to extract entities: %s", e)
            return self._fallback_entity_extraction(article)

    def _fallback_entity_extraction(self, article: Article) -> dict[str, list[str]]:
        """Fallback regex-based entity extraction."""
        text = f"{article.title} {article.content}"
        text_lower = text.lower()

        categories = []
        if "ransomware" in text_lower:
            categories.append("ransomware")
        if "vulnerability" in text_lower or "cve-" in text_lower:
            categories.append("vulnerability")
        if "breach" in text_lower or "leak" in text_lower:
            categories.append("breach")
        if "malware" in text_lower:
            categories.append("malware")
        if "phishing" in text_lower:
            categories.append("phishing")

        # Extract CVEs
        cve_pattern = r"CVE-\d{4}-\d{4,7}"
        vulnerabilities = list(set(re.findall(cve_pattern, text, re.IGNORECASE)))

        return {
            "categories": categories or ["security"],
            "vulnerabilities": vulnerabilities,
            "threat_actors": [],
            "products": [],
        }

    async def process_article(self, article: Article) -> Article:
        """Fully process an article with all intelligence features."""
        logger.info("Processing article: %s", article.id)

        # Generate embedding
        embed_text = f"{article.title}. {article.content[:2000]}"
        article.embedding = await self.generate_embedding(embed_text)

        # Generate summary
        article.summary = await self.generate_summary(article)

        # Extract entities
        entities = await self.extract_entities(article)
        article.categories = entities.get("categories", [])
        article.vulnerabilities = entities.get("vulnerabilities", [])
        article.threat_actors = entities.get("threat_actors", [])

        logger.info(
            "Processed article %s: categories=%s",
            article.id,
            article.categories,
        )
        return article

    def compute_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        if not embedding1 or not embedding2:
            return 0.0

        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    async def find_similar_articles(
        self,
        article: Article,
        all_articles: Optional[list[Article]] = None,
        threshold: float = 0.75,
        max_results: int = 5,
    ) -> list[tuple[Article, float]]:
        """Find articles similar to the given one using vector search."""
        if not article.embedding:
            return []

        # Use database vector similarity search
        try:
            similar_summaries = await self._article_repo.find_similar(
                embedding=article.embedding,
                threshold=threshold,
                limit=max_results,
                exclude_ids=[article.id],
            )

            # Convert summaries to full articles
            results = []
            for summary, similarity in similar_summaries:
                full_article = await self._article_repo.get_by_id(summary.id)
                if full_article:
                    results.append((full_article, similarity))

            return results
        except Exception as e:
            logger.warning("Vector search failed, falling back to in-memory: %s", e)

            # Fallback to in-memory comparison if database search fails
            if not all_articles:
                return []

            similarities = []
            for other in all_articles:
                if other.id == article.id or not other.embedding:
                    continue

                sim = self.compute_similarity(article.embedding, other.embedding)
                if sim >= threshold:
                    similarities.append((other, sim))

            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:max_results]


# Singleton instance
intelligence_service = IntelligenceService()
