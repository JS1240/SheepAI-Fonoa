"""Repository classes for Supabase database operations."""

from app.db.repositories.article_repository import ArticleRepository
from app.db.repositories.graph_repository import GraphRepository
from app.db.repositories.notification_repository import NotificationRepository
from app.db.repositories.prediction_repository import PredictionRepository

__all__ = [
    "ArticleRepository",
    "GraphRepository",
    "NotificationRepository",
    "PredictionRepository",
]
