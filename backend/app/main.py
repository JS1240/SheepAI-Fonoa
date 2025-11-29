"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import router
from app.api.notification_routes import router as notification_router
from app.api.internal_routes import router as internal_router
from app.db import close_supabase_client, get_supabase_client
from app.services.graph import graph_service
from app.services.ingestion import ingestion_service
from app.services.email import email_service
from app.services.notification import notification_service
from app.services.telegram_bot import telegram_bot_service

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Security Intelligence Platform...")
    logger.info("App: %s v%s", settings.app_name, settings.app_version)

    # Log scraper configuration status
    if ingestion_service.is_scraper_configured():
        logger.info("Bright Data scraper: ENABLED")
    else:
        logger.info("Bright Data scraper: DISABLED (credentials not configured)")

    # Initialize Supabase connection
    try:
        logger.info("Initializing Supabase connection...")
        client = get_supabase_client()
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.warning("Supabase initialization failed: %s", e)

    # Load existing data from database
    article_count = 0
    try:
        logger.info("Loading data from database...")
        article_count = await ingestion_service.load_from_database()
        logger.info("Loaded %d articles from database", article_count)

        graph_count = await graph_service.load_from_database()
        logger.info("Loaded %d graph nodes from database", graph_count)
    except Exception as e:
        logger.warning("Database load failed: %s", e)

    # Check if backfill is needed (empty database + scraper configured)
    if article_count == 0 and ingestion_service.is_scraper_configured():
        logger.info("Database is empty - starting automatic backfill...")
        try:
            backfill_articles = await ingestion_service.backfill_archive(
                days_back=settings.archive_backfill_days,
                max_articles=settings.archive_max_articles,
            )
            logger.info("Backfill complete: %d articles ingested", len(backfill_articles))
        except Exception as e:
            logger.error("Automatic backfill failed: %s", e)
            # Fall back to RSS-only ingestion
            logger.info("Falling back to RSS-only ingestion...")
            try:
                articles = await ingestion_service.ingest_articles(use_scraper=False)
                logger.info("RSS fallback ingested %d articles", len(articles))
            except Exception as rss_e:
                logger.warning("RSS fallback also failed: %s", rss_e)
    else:
        # Fetch new articles (hybrid mode if scraper available)
        try:
            logger.info("Fetching new articles...")
            articles = await ingestion_service.ingest_articles()
            logger.info("Ingested %d new articles on startup", len(articles))
        except Exception as e:
            logger.warning("Initial ingestion failed: %s", e)

    # Log scraper metrics if available
    if ingestion_service.is_scraper_configured():
        metrics = ingestion_service.get_scraper_metrics()
        logger.info(
            "Scraper metrics: %d requests, %.1f%% success rate",
            metrics.get("total_requests", 0),
            metrics.get("success_rate", 1.0) * 100,
        )

    # Initialize notification services
    if email_service.is_configured():
        logger.info("Email service: ENABLED (Resend API)")
    else:
        logger.info("Email service: DISABLED (RESEND_API_KEY not configured)")

    if telegram_bot_service.is_configured():
        logger.info("Telegram bot: ENABLED")
        telegram_bot_service.set_link_callback(notification_service.verify_telegram_link)
        await telegram_bot_service.start_polling()
        logger.info("Telegram bot polling started")
    else:
        logger.info("Telegram bot: DISABLED (TELEGRAM_BOT_TOKEN not configured)")

    yield

    # Shutdown
    logger.info("Shutting down Security Intelligence Platform...")
    await telegram_bot_service.close()
    await email_service.close()
    await ingestion_service.close()
    close_supabase_client()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered security intelligence platform that transforms cybersecurity news "
        "into actionable insights through knowledge graphs, story evolution tracking, "
        "and predictive analytics."
    ),
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix=settings.api_prefix)
app.include_router(notification_router, prefix=settings.api_prefix)
app.include_router(internal_router, prefix=settings.api_prefix)


# Root endpoint
@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Security Intelligence Platform API",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
        "demo_query": {
            "endpoint": f"{settings.api_prefix}/chat",
            "method": "POST",
            "example_body": {
                "message": "Show me the latest ransomware story",
                "include_timeline": True,
                "include_graph": True,
                "include_predictions": True,
            },
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
