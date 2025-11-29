"""Notification system data models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DigestFrequency(str, Enum):
    """Frequency options for notification digests."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class NotificationChannel(str, Enum):
    """Supported notification channels."""

    EMAIL = "email"
    TELEGRAM = "telegram"


class NotificationStatus(str, Enum):
    """Status of a notification in the queue."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class UserProfileBase(BaseModel):
    """Base model for user profile data."""

    display_name: Optional[str] = None
    digest_frequency: DigestFrequency = DigestFrequency.DAILY
    email_enabled: bool = True
    telegram_enabled: bool = False


class UserProfileCreate(UserProfileBase):
    """Model for creating a user profile."""

    email: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """Model for updating a user profile."""

    display_name: Optional[str] = None
    digest_frequency: Optional[DigestFrequency] = None
    email_enabled: Optional[bool] = None
    telegram_enabled: Optional[bool] = None


class UserProfile(UserProfileBase):
    """Full user profile model."""

    id: UUID
    email: Optional[str] = None
    last_digest_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class InterestBase(BaseModel):
    """Base model for notification interests."""

    interest_text: str = Field(..., min_length=3, max_length=500)
    similarity_threshold: float = Field(default=0.8, ge=0.5, le=1.0)


class InterestCreate(InterestBase):
    """Model for creating a notification interest."""

    pass


class InterestUpdate(BaseModel):
    """Model for updating a notification interest."""

    interest_text: Optional[str] = Field(None, min_length=3, max_length=500)
    similarity_threshold: Optional[float] = Field(None, ge=0.5, le=1.0)
    is_active: Optional[bool] = None


class Interest(InterestBase):
    """Full notification interest model."""

    id: UUID
    user_id: UUID
    embedding: Optional[list[float]] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class InterestSummary(BaseModel):
    """Summary view of an interest without embedding."""

    id: UUID
    interest_text: str
    similarity_threshold: float
    is_active: bool
    created_at: datetime


class TelegramLinkResponse(BaseModel):
    """Response with Telegram deep link."""

    link_url: str
    link_token: str
    expires_at: datetime


class TelegramLink(BaseModel):
    """Full Telegram link model."""

    id: UUID
    user_id: UUID
    telegram_chat_id: Optional[int] = None
    telegram_username: Optional[str] = None
    is_verified: bool = False
    created_at: datetime
    verified_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class QueuedNotification(BaseModel):
    """A notification in the queue."""

    id: UUID
    user_id: UUID
    article_id: str
    interest_id: Optional[UUID] = None
    similarity_score: float
    channel: NotificationChannel
    status: NotificationStatus
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class NotificationHistoryEntry(BaseModel):
    """A record of sent notifications."""

    id: UUID
    user_id: UUID
    channel: NotificationChannel
    article_count: int
    digest_type: Optional[DigestFrequency] = None
    sent_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class InterestMatch(BaseModel):
    """Result of matching an article to user interests."""

    interest_id: UUID
    user_id: UUID
    interest_text: str
    similarity: float
