"""Notification service for matching articles to user interests."""

import logging
from typing import Optional
from uuid import UUID

from app.config import settings
from app.db.repositories.notification_repository import NotificationRepository
from app.models.article import Article
from app.models.notification import (
    DigestFrequency,
    Interest,
    InterestCreate,
    InterestMatch,
    InterestSummary,
    InterestUpdate,
    NotificationChannel,
    TelegramLink,
    TelegramLinkResponse,
    UserProfile,
    UserProfileCreate,
    UserProfileUpdate,
)
from app.services.intelligence import intelligence_service

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing user notifications and interest matching."""

    def __init__(
        self,
        notification_repo: Optional[NotificationRepository] = None,
    ) -> None:
        self._repo = notification_repo or NotificationRepository()
        self._intelligence = intelligence_service

    async def get_or_create_profile(
        self,
        user_id: UUID,
        email: Optional[str] = None,
    ) -> UserProfile:
        """Get or create a user profile."""
        return await self._repo.get_or_create_profile(user_id, email)

    async def update_profile(
        self,
        user_id: UUID,
        update: UserProfileUpdate,
    ) -> Optional[UserProfile]:
        """Update user profile settings."""
        return await self._repo.update_profile(user_id, update)

    async def create_interest(
        self,
        user_id: UUID,
        interest: InterestCreate,
    ) -> Interest:
        """Create a new notification interest with embedding.

        Generates an embedding for the interest text to enable
        semantic similarity matching against article embeddings.
        """
        logger.info(
            "Creating interest for user %s: %s",
            user_id,
            interest.interest_text[:50],
        )

        embedding = await self._intelligence.generate_embedding(interest.interest_text)

        if not embedding:
            logger.warning("Failed to generate embedding for interest")

        return await self._repo.create_interest(
            user_id=user_id,
            interest=interest,
            embedding=embedding if embedding else None,
        )

    async def get_user_interests(
        self,
        user_id: UUID,
        active_only: bool = True,
    ) -> list[InterestSummary]:
        """Get all interests for a user."""
        return await self._repo.get_user_interests(user_id, active_only)

    async def update_interest(
        self,
        interest_id: UUID,
        user_id: UUID,
        update: InterestUpdate,
    ) -> Optional[Interest]:
        """Update an interest, regenerating embedding if text changed."""
        new_embedding = None
        if update.interest_text:
            new_embedding = await self._intelligence.generate_embedding(
                update.interest_text
            )

        return await self._repo.update_interest(
            interest_id=interest_id,
            user_id=user_id,
            update=update,
            new_embedding=new_embedding,
        )

    async def delete_interest(
        self,
        interest_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete a user interest."""
        return await self._repo.delete_interest(interest_id, user_id)

    async def process_new_article(self, article: Article) -> int:
        """Process a new article and queue notifications for matching interests.

        Matches the article's embedding against all active user interests
        and queues notifications for users with matching preferences.

        Args:
            article: The newly ingested article with embedding.

        Returns:
            Number of notifications queued.
        """
        if not article.embedding:
            logger.warning(
                "Article %s has no embedding, skipping notification matching",
                article.id,
            )
            return 0

        logger.info("Processing article %s for notifications", article.id)

        matches = await self._repo.match_article_to_interests(
            article_embedding=article.embedding,
            threshold=settings.notification_similarity_threshold,
        )

        if not matches:
            logger.debug("No matching interests for article %s", article.id)
            return 0

        logger.info(
            "Found %d matching interests for article %s",
            len(matches),
            article.id,
        )

        queued_count = 0

        user_matches: dict[UUID, list[InterestMatch]] = {}
        for match in matches:
            if match.user_id not in user_matches:
                user_matches[match.user_id] = []
            user_matches[match.user_id].append(match)

        for user_id, user_interest_matches in user_matches.items():
            profile = await self._repo.get_profile(user_id)
            if not profile:
                continue

            best_match = max(user_interest_matches, key=lambda m: m.similarity)

            if profile.email_enabled:
                success = await self._repo.queue_notification(
                    user_id=user_id,
                    article_id=article.id,
                    interest_id=best_match.interest_id,
                    similarity_score=best_match.similarity,
                    channel=NotificationChannel.EMAIL,
                )
                if success:
                    queued_count += 1

            if profile.telegram_enabled:
                telegram_link = await self._repo.get_telegram_link(user_id)
                if telegram_link and telegram_link.is_verified:
                    success = await self._repo.queue_notification(
                        user_id=user_id,
                        article_id=article.id,
                        interest_id=best_match.interest_id,
                        similarity_score=best_match.similarity,
                        channel=NotificationChannel.TELEGRAM,
                    )
                    if success:
                        queued_count += 1

        logger.info(
            "Queued %d notifications for article %s",
            queued_count,
            article.id,
        )
        return queued_count

    async def create_telegram_link(self, user_id: UUID) -> TelegramLinkResponse:
        """Create a Telegram account linking token.

        Generates a unique token that the user can send to the Telegram bot
        to link their account.

        Returns:
            Response with deep link URL and expiration time.
        """
        token, expires_at = await self._repo.create_telegram_link_token(user_id)

        bot_username = settings.telegram_bot_username or "SecurityIntelBot"
        link_url = f"https://t.me/{bot_username}?start={token}"

        return TelegramLinkResponse(
            link_url=link_url,
            link_token=token,
            expires_at=expires_at,
        )

    async def get_telegram_status(self, user_id: UUID) -> Optional[TelegramLink]:
        """Get Telegram link status for a user."""
        return await self._repo.get_telegram_link(user_id)

    async def verify_telegram_link(
        self,
        token: str,
        chat_id: int,
        username: Optional[str] = None,
    ) -> bool:
        """Verify a Telegram link token from the bot.

        Called when a user sends /start {token} to the bot.

        Args:
            token: The linking token from the deep link.
            chat_id: The Telegram chat ID.
            username: The Telegram username (optional).

        Returns:
            True if verification successful.
        """
        user_id = await self._repo.verify_telegram_link(
            token=token,
            chat_id=chat_id,
            username=username,
        )

        if user_id:
            await self._repo.update_profile(
                user_id,
                UserProfileUpdate(telegram_enabled=True),
            )
            logger.info("Telegram linked for user %s", user_id)
            return True

        return False

    async def get_users_for_digest(
        self,
        frequency: DigestFrequency,
    ) -> list[UserProfile]:
        """Get users who should receive a digest notification."""
        return await self._repo.get_users_for_digest(frequency)

    async def get_pending_notifications(
        self,
        user_id: UUID,
        channel: NotificationChannel,
    ) -> list[dict]:
        """Get pending notifications for a user on a specific channel."""
        return await self._repo.get_pending_notifications(user_id, channel)

    async def mark_notifications_sent(
        self,
        notification_ids: list[UUID],
    ) -> int:
        """Mark notifications as sent."""
        return await self._repo.mark_notifications_sent(notification_ids)

    async def record_digest_sent(
        self,
        user_id: UUID,
        channel: NotificationChannel,
        article_count: int,
        digest_type: DigestFrequency,
    ) -> None:
        """Record that a digest was sent to a user."""
        await self._repo.record_notification_sent(
            user_id=user_id,
            channel=channel,
            article_count=article_count,
            digest_type=digest_type,
        )

    async def get_notification_history(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[dict]:
        """Get notification history for a user."""
        return await self._repo.get_notification_history(user_id, limit)


notification_service = NotificationService()
