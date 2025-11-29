"""API routes for notification management."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.notification import (
    Interest,
    InterestCreate,
    InterestSummary,
    InterestUpdate,
    TelegramLink,
    TelegramLinkResponse,
    UserProfile,
    UserProfileUpdate,
)
from app.services.notification import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def get_current_user_id() -> UUID:
    """Get the current user ID from the request.

    In a real implementation, this would extract the user ID from
    the Supabase Auth JWT token in the Authorization header.

    For development, you can pass user_id as a query parameter.
    """
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Pass user_id query param for dev testing.",
    )


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    user_id: Optional[UUID] = Query(None, description="User ID (dev only)"),
) -> UserProfile:
    """Get the current user's notification profile.

    Creates a profile if one doesn't exist.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    profile = await notification_service.get_or_create_profile(user_id)
    return profile


@router.patch("/profile", response_model=UserProfile)
async def update_profile(
    update: UserProfileUpdate,
    user_id: Optional[UUID] = Query(None, description="User ID (dev only)"),
) -> UserProfile:
    """Update the current user's notification settings."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    profile = await notification_service.update_profile(user_id, update)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile


@router.get("/interests", response_model=list[InterestSummary])
async def list_interests(
    user_id: Optional[UUID] = Query(None, description="User ID (dev only)"),
    active_only: bool = Query(True, description="Only return active interests"),
) -> list[InterestSummary]:
    """List all notification interests for the current user."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    interests = await notification_service.get_user_interests(user_id, active_only)
    return interests


@router.post("/interests", response_model=Interest, status_code=201)
async def create_interest(
    interest: InterestCreate,
    user_id: Optional[UUID] = Query(None, description="User ID (dev only)"),
) -> Interest:
    """Create a new notification interest.

    The interest text will be converted to an embedding for
    semantic matching against article content.

    Example interest texts:
    - "ransomware attacks targeting healthcare"
    - "zero-day vulnerabilities in Microsoft products"
    - "nation-state threat actors APT groups"
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    await notification_service.get_or_create_profile(user_id)

    created = await notification_service.create_interest(user_id, interest)
    return created


@router.patch("/interests/{interest_id}", response_model=Interest)
async def update_interest(
    interest_id: UUID,
    update: InterestUpdate,
    user_id: Optional[UUID] = Query(None, description="User ID (dev only)"),
) -> Interest:
    """Update a notification interest.

    If the interest text is changed, the embedding will be regenerated.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    updated = await notification_service.update_interest(interest_id, user_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Interest not found")

    return updated


@router.delete("/interests/{interest_id}", status_code=204)
async def delete_interest(
    interest_id: UUID,
    user_id: Optional[UUID] = Query(None, description="User ID (dev only)"),
) -> None:
    """Delete a notification interest."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    success = await notification_service.delete_interest(interest_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Interest not found")


@router.post("/telegram/link", response_model=TelegramLinkResponse)
async def create_telegram_link(
    user_id: Optional[UUID] = Query(None, description="User ID (dev only)"),
) -> TelegramLinkResponse:
    """Generate a Telegram account linking URL.

    Returns a deep link URL that the user can click to open
    Telegram and link their account. The link expires in 15 minutes.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    await notification_service.get_or_create_profile(user_id)

    link_response = await notification_service.create_telegram_link(user_id)
    return link_response


@router.get("/telegram/status", response_model=Optional[TelegramLink])
async def get_telegram_status(
    user_id: Optional[UUID] = Query(None, description="User ID (dev only)"),
) -> Optional[TelegramLink]:
    """Get the Telegram link status for the current user.

    Returns null if no link exists, or the link details if one exists.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    status = await notification_service.get_telegram_status(user_id)
    return status


@router.get("/history")
async def get_notification_history(
    user_id: Optional[UUID] = Query(None, description="User ID (dev only)"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
) -> list[dict]:
    """Get notification history for the current user.

    Returns a list of past digest notifications with timestamps
    and article counts.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    history = await notification_service.get_notification_history(user_id, limit)
    return history
