"""Internal API routes for Edge Function callbacks and system operations."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.db.repositories import ArticleRepository
from app.models.notification import DigestFrequency, NotificationChannel
from app.services.email import email_service
from app.services.notification import notification_service
from app.services.telegram_bot import telegram_bot_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


def verify_service_key(authorization: Optional[str] = Header(None)) -> None:
    """Verify the request is from a trusted source using the service key.

    In production, this should validate the Supabase service_role key
    or a shared secret with Edge Functions.
    """
    if not settings.internal_api_key:
        return

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")

    expected = f"Bearer {settings.internal_api_key}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid authorization")


@router.post("/process-digest")
async def process_digest(
    frequency: str,
    authorization: Optional[str] = Header(None),
) -> dict:
    """Process and send digest notifications.

    Called by pg_cron via Edge Function at scheduled times:
    - Hourly: 0 * * * *
    - Daily: 0 8 * * * (8 AM UTC)
    - Weekly: 0 8 * * 1 (Monday 8 AM UTC)

    Args:
        frequency: One of 'hourly', 'daily', 'weekly'

    Returns:
        Summary of notifications sent.
    """
    verify_service_key(authorization)

    try:
        digest_frequency = DigestFrequency(frequency)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid frequency: {frequency}. Must be hourly, daily, or weekly.",
        )

    logger.info("Processing %s digest notifications", frequency)

    users = await notification_service.get_users_for_digest(digest_frequency)

    if not users:
        logger.info("No users scheduled for %s digest", frequency)
        return {"processed": 0, "email_sent": 0, "telegram_sent": 0}

    article_repo = ArticleRepository()
    email_sent = 0
    telegram_sent = 0
    errors = []

    for user in users:
        try:
            if user.email_enabled and user.email:
                pending = await notification_service.get_pending_notifications(
                    user.id, NotificationChannel.EMAIL
                )

                if pending:
                    articles = []
                    notification_ids = []

                    for notif in pending:
                        article = await article_repo.get_by_id(notif["article_id"])
                        if article:
                            articles.append({
                                "title": article.title,
                                "url": article.url,
                                "summary": article.summary or "",
                                "similarity_score": notif["similarity_score"],
                                "interest_text": notif.get("interest_text", "your interests"),
                            })
                            notification_ids.append(UUID(notif["id"]))

                    if articles:
                        success = await email_service.send_digest_email(
                            to_email=user.email,
                            articles=articles,
                            digest_type=digest_frequency,
                        )

                        if success:
                            await notification_service.mark_notifications_sent(notification_ids)
                            await notification_service.record_digest_sent(
                                user_id=user.id,
                                channel=NotificationChannel.EMAIL,
                                article_count=len(articles),
                                digest_type=digest_frequency,
                            )
                            email_sent += 1
                        else:
                            errors.append(f"Email failed for user {user.id}")

            if user.telegram_enabled:
                telegram_link = await notification_service.get_telegram_status(user.id)
                if telegram_link and telegram_link.is_verified and telegram_link.telegram_chat_id:
                    pending = await notification_service.get_pending_notifications(
                        user.id, NotificationChannel.TELEGRAM
                    )

                    if pending:
                        articles = []
                        notification_ids = []

                        for notif in pending:
                            article = await article_repo.get_by_id(notif["article_id"])
                            if article:
                                articles.append({
                                    "title": article.title,
                                    "url": article.url,
                                    "summary": article.summary or "",
                                    "similarity_score": notif["similarity_score"],
                                    "interest_text": notif.get("interest_text", "your interests"),
                                })
                                notification_ids.append(UUID(notif["id"]))

                        if articles:
                            success = await telegram_bot_service.send_digest(
                                chat_id=telegram_link.telegram_chat_id,
                                articles=articles,
                                digest_type=digest_frequency,
                            )

                            if success:
                                await notification_service.mark_notifications_sent(notification_ids)
                                await notification_service.record_digest_sent(
                                    user_id=user.id,
                                    channel=NotificationChannel.TELEGRAM,
                                    article_count=len(articles),
                                    digest_type=digest_frequency,
                                )
                                telegram_sent += 1
                            else:
                                errors.append(f"Telegram failed for user {user.id}")

        except Exception as e:
            logger.error("Error processing digest for user %s: %s", user.id, e)
            errors.append(f"Error for user {user.id}: {str(e)}")

    result = {
        "processed": len(users),
        "email_sent": email_sent,
        "telegram_sent": telegram_sent,
    }

    if errors:
        result["errors"] = errors[:10]

    logger.info(
        "Digest processing complete: %d users, %d emails, %d telegrams",
        len(users),
        email_sent,
        telegram_sent,
    )

    return result


@router.post("/telegram/webhook")
async def telegram_webhook(
    token: str,
    chat_id: int,
    username: Optional[str] = None,
    authorization: Optional[str] = Header(None),
) -> dict:
    """Handle Telegram account linking from the bot.

    Called when a user sends /start {token} to the Telegram bot.
    The bot should call this endpoint to verify the token and link the account.

    Args:
        token: The linking token from the deep link.
        chat_id: The Telegram chat ID.
        username: The Telegram username (optional).

    Returns:
        Success status.
    """
    verify_service_key(authorization)

    success = await notification_service.verify_telegram_link(
        token=token,
        chat_id=chat_id,
        username=username,
    )

    if success:
        return {"status": "linked", "message": "Account linked successfully"}

    return {"status": "failed", "message": "Invalid or expired token"}


@router.get("/health")
async def internal_health() -> dict:
    """Health check for internal services."""
    return {
        "status": "healthy",
        "email_configured": email_service.is_configured(),
        "telegram_configured": telegram_bot_service.is_configured(),
    }
