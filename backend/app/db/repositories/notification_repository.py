"""Notification repository for Supabase database operations."""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from supabase import Client

from app.db.supabase_client import get_supabase_client
from app.models.notification import (
    DigestFrequency,
    Interest,
    InterestCreate,
    InterestMatch,
    InterestSummary,
    InterestUpdate,
    NotificationChannel,
    NotificationHistoryEntry,
    NotificationStatus,
    QueuedNotification,
    TelegramLink,
    UserProfile,
    UserProfileUpdate,
)

logger = logging.getLogger(__name__)


class NotificationRepository:
    """Repository for notification CRUD operations."""

    def __init__(self, client: Optional[Client] = None):
        """Initialize the repository with a Supabase client."""
        self._client = client

    @property
    def client(self) -> Client:
        """Get the Supabase client (lazy initialization)."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def get_or_create_profile(self, user_id: UUID, email: Optional[str] = None) -> UserProfile:
        """Get or create a user profile."""
        try:
            result = self.client.table("user_profiles").select("*").eq("id", str(user_id)).single().execute()
            if result.data:
                return self._row_to_profile(result.data)
        except Exception:
            pass

        data = {
            "id": str(user_id),
            "email": email,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        result = self.client.table("user_profiles").insert(data).execute()
        return self._row_to_profile(result.data[0])

    async def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Get a user profile by ID."""
        try:
            result = self.client.table("user_profiles").select("*").eq("id", str(user_id)).single().execute()
            if result.data:
                return self._row_to_profile(result.data)
            return None
        except Exception as e:
            logger.debug("Profile not found for user %s: %s", user_id, e)
            return None

    async def update_profile(self, user_id: UUID, update: UserProfileUpdate) -> Optional[UserProfile]:
        """Update a user profile."""
        data = {k: v.value if isinstance(v, DigestFrequency) else v for k, v in update.model_dump().items() if v is not None}
        if not data:
            return await self.get_profile(user_id)

        data["updated_at"] = datetime.utcnow().isoformat()

        try:
            result = self.client.table("user_profiles").update(data).eq("id", str(user_id)).execute()
            if result.data:
                return self._row_to_profile(result.data[0])
            return None
        except Exception as e:
            logger.error("Failed to update profile %s: %s", user_id, e)
            return None

    async def get_users_for_digest(self, digest_type: DigestFrequency) -> list[UserProfile]:
        """Get users due for a specific digest type."""
        try:
            result = self.client.table("user_profiles").select("*").eq("digest_frequency", digest_type.value).execute()
            return [self._row_to_profile(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get users for digest: %s", e)
            return []

    async def create_interest(self, user_id: UUID, interest: InterestCreate, embedding: list[float]) -> Interest:
        """Create a new notification interest."""
        data = {
            "user_id": str(user_id),
            "interest_text": interest.interest_text,
            "embedding": embedding,
            "similarity_threshold": interest.similarity_threshold,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        result = self.client.table("notification_interests").insert(data).execute()
        return self._row_to_interest(result.data[0])

    async def get_user_interests(self, user_id: UUID, active_only: bool = True) -> list[InterestSummary]:
        """Get all interests for a user."""
        try:
            query = (
                self.client.table("notification_interests")
                .select("id, interest_text, similarity_threshold, is_active, created_at")
                .eq("user_id", str(user_id))
            )
            if active_only:
                query = query.eq("is_active", True)

            result = query.order("created_at", desc=True).execute()
            return [
                InterestSummary(
                    id=UUID(row["id"]),
                    interest_text=row["interest_text"],
                    similarity_threshold=row["similarity_threshold"],
                    is_active=row["is_active"],
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                )
                for row in result.data
            ]
        except Exception as e:
            logger.error("Failed to get interests for user %s: %s", user_id, e)
            return []

    async def get_interest(self, interest_id: UUID, user_id: UUID) -> Optional[Interest]:
        """Get a specific interest by ID."""
        try:
            result = (
                self.client.table("notification_interests")
                .select("*")
                .eq("id", str(interest_id))
                .eq("user_id", str(user_id))
                .single()
                .execute()
            )
            if result.data:
                return self._row_to_interest(result.data)
            return None
        except Exception:
            return None

    async def update_interest(
        self,
        interest_id: UUID,
        user_id: UUID,
        update: InterestUpdate,
        embedding: Optional[list[float]] = None,
    ) -> Optional[Interest]:
        """Update a notification interest."""
        data = {k: v for k, v in update.model_dump().items() if v is not None}
        if embedding:
            data["embedding"] = embedding
        if not data:
            return await self.get_interest(interest_id, user_id)

        data["updated_at"] = datetime.utcnow().isoformat()

        try:
            result = (
                self.client.table("notification_interests")
                .update(data)
                .eq("id", str(interest_id))
                .eq("user_id", str(user_id))
                .execute()
            )
            if result.data:
                return self._row_to_interest(result.data[0])
            return None
        except Exception as e:
            logger.error("Failed to update interest %s: %s", interest_id, e)
            return None

    async def delete_interest(self, interest_id: UUID, user_id: UUID) -> bool:
        """Delete a notification interest."""
        try:
            result = (
                self.client.table("notification_interests")
                .delete()
                .eq("id", str(interest_id))
                .eq("user_id", str(user_id))
                .execute()
            )
            return len(result.data) > 0
        except Exception as e:
            logger.error("Failed to delete interest %s: %s", interest_id, e)
            return False

    async def match_article_to_interests(
        self,
        article_embedding: list[float],
        threshold: float = 0.8,
    ) -> list[InterestMatch]:
        """Find interests that match an article embedding."""
        try:
            result = self.client.rpc(
                "match_article_to_interests",
                {
                    "article_embedding": article_embedding,
                    "min_threshold": threshold,
                },
            ).execute()

            return [
                InterestMatch(
                    interest_id=UUID(row["interest_id"]),
                    user_id=UUID(row["user_id"]),
                    interest_text=row["interest_text"],
                    similarity=row["similarity"],
                )
                for row in result.data
            ]
        except Exception as e:
            logger.error("Failed to match article to interests: %s", e)
            return []

    async def create_telegram_link_token(self, user_id: UUID) -> tuple[str, datetime]:
        """Create a new Telegram link token."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        try:
            self.client.table("telegram_links").delete().eq("user_id", str(user_id)).eq("is_verified", False).execute()
        except Exception:
            pass

        data = {
            "user_id": str(user_id),
            "link_token": token,
            "token_expires_at": expires_at.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }
        self.client.table("telegram_links").insert(data).execute()
        return token, expires_at

    async def verify_telegram_link(self, token: str, chat_id: int, username: Optional[str] = None) -> Optional[UUID]:
        """Verify a Telegram link token and associate chat ID."""
        try:
            result = (
                self.client.table("telegram_links")
                .select("id, user_id")
                .eq("link_token", token)
                .gt("token_expires_at", datetime.utcnow().isoformat())
                .eq("is_verified", False)
                .single()
                .execute()
            )

            if not result.data:
                return None

            link_id = result.data["id"]
            user_id = UUID(result.data["user_id"])

            update_data = {
                "telegram_chat_id": chat_id,
                "telegram_username": username,
                "is_verified": True,
                "verified_at": datetime.utcnow().isoformat(),
                "link_token": None,
                "token_expires_at": None,
            }
            self.client.table("telegram_links").update(update_data).eq("id", link_id).execute()
            self.client.table("user_profiles").update({"telegram_enabled": True}).eq("id", str(user_id)).execute()

            return user_id
        except Exception as e:
            logger.error("Failed to verify Telegram link: %s", e)
            return None

    async def get_telegram_link(self, user_id: UUID) -> Optional[TelegramLink]:
        """Get Telegram link for a user."""
        try:
            result = (
                self.client.table("telegram_links")
                .select("*")
                .eq("user_id", str(user_id))
                .eq("is_verified", True)
                .single()
                .execute()
            )
            if result.data:
                return self._row_to_telegram_link(result.data)
            return None
        except Exception:
            return None

    async def delete_telegram_link(self, user_id: UUID) -> bool:
        """Delete Telegram link for a user."""
        try:
            self.client.table("telegram_links").delete().eq("user_id", str(user_id)).execute()
            self.client.table("user_profiles").update({"telegram_enabled": False}).eq("id", str(user_id)).execute()
            return True
        except Exception as e:
            logger.error("Failed to delete Telegram link: %s", e)
            return False

    async def queue_notification(
        self,
        user_id: UUID,
        article_id: str,
        channel: NotificationChannel,
        similarity_score: float,
        interest_id: Optional[UUID] = None,
    ) -> Optional[QueuedNotification]:
        """Add a notification to the queue."""
        data = {
            "user_id": str(user_id),
            "article_id": article_id,
            "channel": channel.value,
            "similarity_score": similarity_score,
            "interest_id": str(interest_id) if interest_id else None,
            "status": NotificationStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
        }
        try:
            result = (
                self.client.table("notification_queue")
                .upsert(data, on_conflict="user_id,article_id,channel")
                .execute()
            )
            if result.data:
                return self._row_to_queued_notification(result.data[0])
            return None
        except Exception as e:
            logger.error("Failed to queue notification: %s", e)
            return None

    async def get_pending_notifications(
        self,
        user_id: UUID,
        channel: NotificationChannel,
        limit: int = 50,
    ) -> list[QueuedNotification]:
        """Get pending notifications for a user and channel."""
        try:
            result = (
                self.client.table("notification_queue")
                .select("*")
                .eq("user_id", str(user_id))
                .eq("channel", channel.value)
                .eq("status", NotificationStatus.PENDING.value)
                .order("similarity_score", desc=True)
                .limit(limit)
                .execute()
            )
            return [self._row_to_queued_notification(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get pending notifications: %s", e)
            return []

    async def mark_notifications_sent(self, notification_ids: list[UUID]) -> int:
        """Mark notifications as sent."""
        if not notification_ids:
            return 0
        try:
            result = (
                self.client.table("notification_queue")
                .update({"status": NotificationStatus.SENT.value, "sent_at": datetime.utcnow().isoformat()})
                .in_("id", [str(nid) for nid in notification_ids])
                .execute()
            )
            return len(result.data)
        except Exception as e:
            logger.error("Failed to mark notifications sent: %s", e)
            return 0

    async def mark_notification_failed(self, notification_id: UUID, error: str) -> bool:
        """Mark a notification as failed."""
        try:
            self.client.table("notification_queue").update(
                {"status": NotificationStatus.FAILED.value, "error_message": error}
            ).eq("id", str(notification_id)).execute()
            return True
        except Exception as e:
            logger.error("Failed to mark notification failed: %s", e)
            return False

    async def record_notification_sent(
        self,
        user_id: UUID,
        channel: NotificationChannel,
        article_count: int,
        digest_type: Optional[DigestFrequency] = None,
    ) -> None:
        """Record a notification in history."""
        data = {
            "user_id": str(user_id),
            "channel": channel.value,
            "article_count": article_count,
            "digest_type": digest_type.value if digest_type else None,
            "sent_at": datetime.utcnow().isoformat(),
        }
        try:
            self.client.table("notification_history").insert(data).execute()
            self.client.table("user_profiles").update(
                {"last_digest_sent_at": datetime.utcnow().isoformat()}
            ).eq("id", str(user_id)).execute()
        except Exception as e:
            logger.error("Failed to record notification history: %s", e)

    async def get_notification_history(self, user_id: UUID, limit: int = 20) -> list[NotificationHistoryEntry]:
        """Get notification history for a user."""
        try:
            result = (
                self.client.table("notification_history")
                .select("*")
                .eq("user_id", str(user_id))
                .order("sent_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [self._row_to_history_entry(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get notification history: %s", e)
            return []

    def _row_to_profile(self, row: dict) -> UserProfile:
        """Convert database row to UserProfile model."""
        return UserProfile(
            id=UUID(row["id"]),
            email=row.get("email"),
            display_name=row.get("display_name"),
            digest_frequency=DigestFrequency(row.get("digest_frequency", "daily")),
            email_enabled=row.get("email_enabled", True),
            telegram_enabled=row.get("telegram_enabled", False),
            last_digest_sent_at=datetime.fromisoformat(row["last_digest_sent_at"].replace("Z", "+00:00"))
            if row.get("last_digest_sent_at")
            else None,
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
        )

    def _row_to_interest(self, row: dict) -> Interest:
        """Convert database row to Interest model."""
        embedding = row.get("embedding")
        if embedding and isinstance(embedding, str):
            import json
            try:
                embedding = json.loads(embedding)
            except (json.JSONDecodeError, TypeError):
                embedding = None

        return Interest(
            id=UUID(row["id"]),
            user_id=UUID(row["user_id"]),
            interest_text=row["interest_text"],
            embedding=embedding,
            similarity_threshold=row.get("similarity_threshold", 0.8),
            is_active=row.get("is_active", True),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
        )

    def _row_to_telegram_link(self, row: dict) -> TelegramLink:
        """Convert database row to TelegramLink model."""
        return TelegramLink(
            id=UUID(row["id"]),
            user_id=UUID(row["user_id"]),
            telegram_chat_id=row.get("telegram_chat_id"),
            telegram_username=row.get("telegram_username"),
            is_verified=row.get("is_verified", False),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            verified_at=datetime.fromisoformat(row["verified_at"].replace("Z", "+00:00"))
            if row.get("verified_at")
            else None,
        )

    def _row_to_queued_notification(self, row: dict) -> QueuedNotification:
        """Convert database row to QueuedNotification model."""
        return QueuedNotification(
            id=UUID(row["id"]),
            user_id=UUID(row["user_id"]),
            article_id=row["article_id"],
            interest_id=UUID(row["interest_id"]) if row.get("interest_id") else None,
            similarity_score=row["similarity_score"],
            channel=NotificationChannel(row["channel"]),
            status=NotificationStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
        )

    def _row_to_history_entry(self, row: dict) -> NotificationHistoryEntry:
        """Convert database row to NotificationHistoryEntry model."""
        return NotificationHistoryEntry(
            id=UUID(row["id"]),
            user_id=UUID(row["user_id"]),
            channel=NotificationChannel(row["channel"]),
            article_count=row["article_count"],
            digest_type=DigestFrequency(row["digest_type"]) if row.get("digest_type") else None,
            sent_at=datetime.fromisoformat(row["sent_at"].replace("Z", "+00:00")),
        )
