"""Supabase client initialization and management."""

import logging
from typing import Optional

from supabase import create_client, Client

from app.config import settings

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create the Supabase client singleton."""
    global _supabase_client

    if _supabase_client is None:
        logger.info("Initializing Supabase client")
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )
        logger.info("Supabase client initialized successfully")

    return _supabase_client


def close_supabase_client() -> None:
    """Close the Supabase client connection."""
    global _supabase_client

    if _supabase_client is not None:
        logger.info("Closing Supabase client")
        _supabase_client = None
