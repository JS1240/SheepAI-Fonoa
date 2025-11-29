"""API routes for the Security Intelligence Platform."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.article import Article, ArticleSummary
from app.models.conversation import (
    ConversationRequest,
    ConversationResponse,
    ExplainToRequest,
    ExplainToResponse,
)
from app.models.graph import GraphVisualization
from app.models.infographic import (
    Infographic,
    InfographicRequest,
    InfographicResponse,
    InfographicType,
)
from app.models.prediction import ThreatDNA, ThreatForecast, ThreatPrediction, PredictionType
from app.services.chat import chat_service
from app.services.graph import graph_service
from app.services.infographic import infographic_service
from app.services.ingestion import ingestion_service
from app.services.intelligence import intelligence_service
from app.services.notification import notification_service
from app.services.prediction import prediction_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Health check
@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Security Intelligence Platform",
        "version": "0.1.0",
    }


# Chat endpoint - the main interface
@router.post("/chat", response_model=ConversationResponse)
async def chat(request: ConversationRequest) -> ConversationResponse:
    """
    Process a natural language query and return intelligence.

    This is the primary interface for the demo:
    - "Show me the latest ransomware story"
    - "What's connected to the Apache vulnerability?"
    - "How has the Log4j situation evolved?"
    """
    try:
        response = await chat_service.process_query(request)
        return response
    except Exception as e:
        logger.error("Chat processing error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# Explain It To... endpoint - audience translation
@router.post("/explain-to", response_model=ExplainToResponse)
async def explain_to_audience(request: ExplainToRequest) -> ExplainToResponse:
    """
    Translate threat content for a specific audience.

    Innovation feature: "Explain It To..." Button
    - CEO: Business impact, dollars, decisions needed
    - Board: Risk framing, governance implications
    - Developers: Technical details, remediation steps

    Example:
    POST /api/explain-to
    {
        "content": "Critical RCE vulnerability CVE-2025-1234 in Apache Struts...",
        "audience": "ceo"
    }
    """
    try:
        response = await chat_service.translate_for_audience(request)
        return response
    except Exception as e:
        logger.error("Translation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# Articles endpoints
@router.get("/articles", response_model=list[ArticleSummary])
async def list_articles(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    days: int = Query(7, ge=1, le=90, description="Days to look back"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
) -> list[ArticleSummary]:
    """List articles with optional filters."""
    categories = [category] if category else None
    articles = await ingestion_service.search_articles(
        query=q,
        categories=categories,
        days=days,
    )

    return [
        ArticleSummary(
            id=a.id,
            title=a.title,
            url=a.url,
            summary=a.summary,
            published_at=a.published_at,
            categories=a.categories,
        )
        for a in articles[:limit]
    ]


@router.get("/articles/{article_id}", response_model=Article)
async def get_article(article_id: str) -> Article:
    """Get a specific article by ID."""
    article = await ingestion_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("/articles/{article_id}/timeline")
async def get_article_timeline(article_id: str):
    """Get the story timeline for an article."""
    article = await ingestion_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Get related articles for timeline
    all_articles = await ingestion_service.get_all_articles()
    similar = await intelligence_service.find_similar_articles(
        article, all_articles, threshold=0.6
    )

    related_articles = [article] + [a for a, _ in similar]

    # Build timeline through chat service
    timeline = await chat_service._build_timeline(article, related_articles)
    return timeline


@router.get("/articles/{article_id}/connections", response_model=GraphVisualization)
async def get_article_connections(
    article_id: str,
    depth: int = Query(2, ge=1, le=5, description="Graph depth"),
) -> GraphVisualization:
    """Get the knowledge graph connections for an article."""
    article = await ingestion_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    graph_data = graph_service.get_subgraph(article_id, depth=depth)
    return graph_data


# Predictions endpoints
@router.get("/predictions", response_model=list[ThreatPrediction])
async def get_predictions(
    article_id: Optional[str] = Query(None, description="Filter by article"),
    prediction_type: Optional[str] = Query(None, description="Prediction type"),
) -> list[ThreatPrediction]:
    """Get predictions, optionally filtered."""
    if article_id:
        article = await ingestion_service.get_article_by_id(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        types = None
        if prediction_type:
            try:
                types = [PredictionType(prediction_type)]
            except ValueError:
                pass

        return await prediction_service.get_predictions_for_article(article, types)

    return []


@router.get("/forecast/{article_id}", response_model=ThreatForecast)
async def get_threat_forecast(article_id: str) -> ThreatForecast:
    """Generate a 48-hour threat forecast for an article.

    Innovation feature: 48-Hour Threat Forecast
    - Hourly risk progression visualization
    - Peak risk identification with timing
    - Key milestones and recommended actions
    - Confidence scoring

    Example response:
    {
        "forecast_id": "fc-2025-001",
        "threat_name": "Apache Struts RCE Vulnerability",
        "peak_risk_hour": 18,
        "peak_risk_level": 0.85,
        "urgency_level": "CRITICAL",
        "summary": "Risk expected to escalate..."
    }
    """
    article = await ingestion_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    try:
        forecast = await prediction_service.generate_48_hour_forecast(article)
        return forecast
    except Exception as e:
        logger.error("Forecast generation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dna/{article_id}", response_model=ThreatDNA)
async def get_threat_dna(article_id: str) -> ThreatDNA:
    """Generate threat DNA analysis with historical pattern matching.

    Innovation feature: Threat DNA Matching
    - Identifies historical threat patterns similar to current threat
    - Maps MITRE ATT&CK techniques and attack vectors
    - Shows what happened with similar threats in the past
    - Provides lessons learned and recommended defenses

    Example response:
    {
        "dna_id": "dna-2025-001",
        "threat_name": "Apache Struts RCE Vulnerability",
        "threat_type": "Remote Code Execution",
        "matches": [
            {
                "historical_title": "Log4Shell Vulnerability",
                "similarity_score": 0.85,
                "historical_outcome": "Massive exploitation within 48 hours"
            }
        ]
    }
    """
    article = await ingestion_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    try:
        dna = await prediction_service.generate_threat_dna(article, graph_service)
        return dna
    except Exception as e:
        logger.error("DNA generation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predictions/{article_id}", response_model=ThreatPrediction)
async def generate_prediction(
    article_id: str,
    prediction_type: str = Query("exploit_likelihood"),
) -> ThreatPrediction:
    """Generate a new prediction for an article."""
    article = await ingestion_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    try:
        pred_type = PredictionType(prediction_type)
    except ValueError:
        pred_type = PredictionType.EXPLOIT_LIKELIHOOD

    prediction = await prediction_service.generate_prediction(article, pred_type)
    if not prediction:
        raise HTTPException(status_code=500, detail="Failed to generate prediction")

    return prediction


# Ingestion endpoints (internal use)
@router.post("/ingest")
async def trigger_ingestion() -> dict:
    """Manually trigger article ingestion."""
    articles = await ingestion_service.ingest_articles()

    # Process each article
    processed = 0
    notifications_queued = 0
    for article in articles:
        try:
            await intelligence_service.process_article(article)

            # Add to graph
            await graph_service.add_article_node(article)

            # Find and connect similar articles
            all_articles = await ingestion_service.get_all_articles()
            similar = await intelligence_service.find_similar_articles(
                article, all_articles
            )
            await graph_service.connect_similar_articles(article, similar)

            # Process notifications for matching user interests
            try:
                queued = await notification_service.process_new_article(article)
                notifications_queued += queued
            except Exception as notif_e:
                logger.warning("Failed to process notifications for article %s: %s", article.id, notif_e)

            processed += 1
        except Exception as e:
            logger.error("Failed to process article %s: %s", article.id, e)

    return {
        "ingested": len(articles),
        "processed": processed,
        "notifications_queued": notifications_queued,
        "graph_stats": graph_service.get_statistics(),
    }


# Build graph from existing articles
@router.post("/graph/build")
async def build_graph(
    limit: int = Query(50, ge=1, le=100, description="Max articles to process"),
    process_entities: bool = Query(True, description="Extract entities with AI if missing"),
) -> dict:
    """Build knowledge graph from existing articles in the database.

    If process_entities is True, articles without categories/vulnerabilities/threat_actors
    will be processed with AI to extract these entities before adding to the graph.
    """
    all_articles = await ingestion_service.get_all_articles(limit=limit)

    processed = 0
    ai_processed = 0
    errors = 0

    for article in all_articles:
        try:
            # Check if article needs entity extraction
            needs_processing = process_entities and (
                not article.categories
                and not article.vulnerabilities
                and not article.threat_actors
            )

            if needs_processing:
                # Process article with AI to extract entities
                article = await intelligence_service.process_article(article)
                # Update article in database with extracted entities
                await ingestion_service.update_article(article)
                ai_processed += 1
                logger.info(
                    "AI processed article %s: categories=%s, vulns=%s, actors=%s",
                    article.id,
                    article.categories,
                    article.vulnerabilities,
                    article.threat_actors,
                )

            # Add to graph (creates article node and entity nodes)
            await graph_service.add_article_node(article)
            processed += 1
        except Exception as e:
            logger.error("Failed to process/add article %s to graph: %s", article.id, e)
            errors += 1

    # Connect similar articles
    for article in all_articles:
        try:
            similar = await intelligence_service.find_similar_articles(
                article, all_articles, threshold=0.5
            )
            await graph_service.connect_similar_articles(article, similar)
        except Exception as e:
            logger.warning("Failed to connect similar articles for %s: %s", article.id, e)

    return {
        "articles_found": len(all_articles),
        "processed": processed,
        "ai_processed": ai_processed,
        "errors": errors,
        "graph_stats": graph_service.get_statistics(),
    }


# Graph statistics
@router.get("/graph/stats")
async def get_graph_stats() -> dict:
    """Get knowledge graph statistics."""
    return graph_service.get_statistics()


# Admin endpoints for scraper management
@router.get("/admin/scraper-health")
async def get_scraper_health() -> dict:
    """Get Bright Data scraper health and metrics.

    Returns configuration status, request counts, success rate, and recent errors.
    """
    metrics = ingestion_service.get_scraper_metrics()
    return {
        "scraper": metrics,
        "settings": {
            "rate_limit_seconds": 2.0,
            "concurrency": 3,
            "timeout_seconds": 60,
        },
    }


@router.post("/admin/backfill")
async def trigger_backfill(
    days_back: int = Query(30, ge=1, le=90, description="Days of history to scrape"),
    max_articles: int = Query(100, ge=1, le=500, description="Max articles to scrape"),
    process_entities: bool = Query(True, description="Process articles with AI after scraping"),
) -> dict:
    """Manually trigger archive backfill using Bright Data scraper.

    This scrapes historical articles from The Hacker News archive.
    Only available if Bright Data credentials are configured.
    """
    if not ingestion_service.is_scraper_configured():
        raise HTTPException(
            status_code=400,
            detail="Bright Data scraper not configured. Set BRIGHTDATA_API_KEY and BRIGHTDATA_ZONE_NAME.",
        )

    try:
        articles = await ingestion_service.backfill_archive(
            days_back=days_back,
            max_articles=max_articles,
        )

        # Optionally process with AI
        ai_processed = 0
        if process_entities:
            for article in articles:
                try:
                    processed_article = await intelligence_service.process_article(article)
                    await ingestion_service.update_article(processed_article)
                    await graph_service.add_article_node(processed_article)
                    ai_processed += 1
                except Exception as e:
                    logger.warning("Failed to process backfilled article %s: %s", article.id, e)

        return {
            "status": "completed",
            "articles_scraped": len(articles),
            "articles_processed": ai_processed,
            "scraper_metrics": ingestion_service.get_scraper_metrics(),
        }
    except Exception as e:
        logger.error("Backfill failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Backfill failed: {str(e)}")


@router.post("/admin/enhance")
async def enhance_rss_articles(
    limit: int = Query(20, ge=1, le=100, description="Max articles to enhance"),
) -> dict:
    """Enhance RSS-only articles with full scraped content.

    Finds articles that were ingested via RSS (summary only) and scrapes
    the full article content using Bright Data.
    """
    if not ingestion_service.is_scraper_configured():
        raise HTTPException(
            status_code=400,
            detail="Bright Data scraper not configured. Set BRIGHTDATA_API_KEY and BRIGHTDATA_ZONE_NAME.",
        )

    try:
        enhanced_count = await ingestion_service.enhance_all_rss_articles(limit=limit)
        return {
            "status": "completed",
            "articles_enhanced": enhanced_count,
            "scraper_metrics": ingestion_service.get_scraper_metrics(),
        }
    except Exception as e:
        logger.error("Enhancement failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Enhancement failed: {str(e)}")


@router.post("/admin/scrape-article")
async def scrape_single_article(
    url: str = Query(..., description="Article URL to scrape"),
    process_entities: bool = Query(True, description="Process with AI after scraping"),
) -> dict:
    """Scrape a single article by URL.

    Useful for testing scraper configuration or manually adding specific articles.
    """
    if not ingestion_service.is_scraper_configured():
        raise HTTPException(
            status_code=400,
            detail="Bright Data scraper not configured. Set BRIGHTDATA_API_KEY and BRIGHTDATA_ZONE_NAME.",
        )

    # Check if article already exists
    article_id = ingestion_service._generate_article_id(url)
    existing = await ingestion_service.get_article_by_id(article_id)
    if existing:
        return {
            "status": "exists",
            "article_id": article_id,
            "message": "Article already exists in database",
        }

    try:
        from app.services.scraper import scraper_service

        scraped = await scraper_service.scrape_article(url)
        if not scraped:
            raise HTTPException(status_code=500, detail="Failed to scrape article")

        article = ingestion_service._scraped_to_article(scraped)

        # Save to database
        from app.db.repositories import ArticleRepository
        repo = ArticleRepository()
        await repo.create(article)

        # Process with AI if requested
        if process_entities:
            try:
                article = await intelligence_service.process_article(article)
                await ingestion_service.update_article(article)
                await graph_service.add_article_node(article)
            except Exception as e:
                logger.warning("Failed to process scraped article: %s", e)

        return {
            "status": "created",
            "article_id": article.id,
            "title": article.title,
            "content_length": len(article.content),
            "author": article.author,
            "tags": article.tags,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Single article scrape failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Scrape failed: {str(e)}")


# Infographic endpoints
@router.get("/articles/{article_id}/infographics")
async def list_article_infographics(article_id: str) -> dict:
    """List existing infographics for an article.

    Returns URLs for any previously generated infographics.
    """
    article = await ingestion_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    infographics = {}
    for infographic_type in InfographicType:
        url = await infographic_service.get_existing_infographic(
            article_id=article_id,
            infographic_type=infographic_type,
        )
        if url:
            infographics[infographic_type.value] = url

    return {
        "article_id": article_id,
        "infographics": infographics,
    }


@router.post("/articles/{article_id}/infographics/{infographic_type}", response_model=InfographicResponse)
async def generate_infographic(
    article_id: str,
    infographic_type: str,
    force_regenerate: bool = Query(False, description="Force regeneration even if exists"),
) -> InfographicResponse:
    """Generate an infographic for an article.

    Infographic types:
    - threat_summary: Visual summary of threats, vulnerabilities, and actors
    - timeline: Story evolution timeline with predictions
    - knowledge_graph: Visual representation of entity connections

    Returns cached version if exists, unless force_regenerate is True.
    """
    article = await ingestion_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Validate infographic type
    try:
        info_type = InfographicType(infographic_type)
    except ValueError:
        valid_types = [t.value for t in InfographicType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid infographic type. Valid types: {valid_types}",
        )

    # Check for existing infographic
    if not force_regenerate:
        existing_url = await infographic_service.get_existing_infographic(
            article_id=article_id,
            infographic_type=info_type,
        )
        if existing_url:
            return InfographicResponse(
                infographic=Infographic(
                    id=f"{article_id}-{info_type.value}",
                    article_id=article_id,
                    infographic_type=info_type,
                    status="completed",
                    public_url=existing_url,
                ),
                is_cached=True,
            )

    # Gather additional data based on type
    graph = None
    predictions = None
    timeline_events = None

    if info_type == InfographicType.KNOWLEDGE_GRAPH:
        graph = graph_service.get_subgraph(article_id, depth=2)
    elif info_type == InfographicType.TIMELINE:
        predictions = await prediction_service.get_predictions_for_article(article)
        # Get related articles for timeline
        all_articles = await ingestion_service.get_all_articles()
        similar = await intelligence_service.find_similar_articles(
            article, all_articles, threshold=0.6
        )
        related_articles = [article] + [a for a, _ in similar]
        timeline_data = await chat_service._build_timeline(article, related_articles)
        if timeline_data:
            timeline_events = timeline_data.events if hasattr(timeline_data, 'events') else []

    # Generate the infographic
    infographic = await infographic_service.generate_infographic(
        article=article,
        infographic_type=info_type,
        graph=graph,
        predictions=predictions,
        timeline_events=timeline_events,
    )

    if infographic.status == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate infographic: {infographic.error_message}",
        )

    return InfographicResponse(
        infographic=infographic,
        is_cached=False,
    )
