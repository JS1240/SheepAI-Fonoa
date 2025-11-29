"""Prediction repository for Supabase database operations."""

import logging
from datetime import datetime
from typing import Optional

from supabase import Client

from app.db.supabase_client import get_supabase_client
from app.models.prediction import PredictionType, ThreatPrediction

logger = logging.getLogger(__name__)


class PredictionRepository:
    """Repository for prediction CRUD operations."""

    def __init__(self, client: Optional[Client] = None):
        """Initialize the repository with a Supabase client."""
        self._client = client

    @property
    def client(self) -> Client:
        """Get the Supabase client (lazy initialization)."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def create(self, prediction: ThreatPrediction) -> ThreatPrediction:
        """Create a new prediction in the database."""
        data = {
            "prediction_id": prediction.prediction_id,
            "article_id": prediction.article_id,
            "prediction_type": prediction.prediction_type.value,
            "description": prediction.description,
            "confidence": prediction.confidence,
            "timeframe_days": prediction.timeframe_days,
            "reasoning": prediction.reasoning,
            "supporting_evidence": prediction.supporting_evidence,
            "expires_at": (
                prediction.expires_at.isoformat() if prediction.expires_at else None
            ),
            "created_at": prediction.generated_at.isoformat(),
        }

        try:
            result = self.client.table("predictions").insert(data).execute()
            logger.info("Created prediction: %s", prediction.prediction_id)
            return prediction
        except Exception as e:
            logger.error(
                "Failed to create prediction %s: %s", prediction.prediction_id, str(e)
            )
            raise

    async def get_by_id(self, prediction_id: str) -> Optional[ThreatPrediction]:
        """Get a prediction by its ID."""
        try:
            result = (
                self.client.table("predictions")
                .select("*")
                .eq("prediction_id", prediction_id)
                .single()
                .execute()
            )

            if result.data:
                return self._row_to_prediction(result.data)
            return None
        except Exception as e:
            logger.error("Failed to get prediction %s: %s", prediction_id, str(e))
            return None

    async def get_by_article_id(self, article_id: str) -> list[ThreatPrediction]:
        """Get all predictions for a specific article."""
        try:
            result = (
                self.client.table("predictions")
                .select("*")
                .eq("article_id", article_id)
                .order("created_at", desc=True)
                .execute()
            )

            return [self._row_to_prediction(row) for row in result.data]
        except Exception as e:
            logger.error(
                "Failed to get predictions for article %s: %s", article_id, str(e)
            )
            return []

    async def get_all(
        self,
        limit: int = 50,
        offset: int = 0,
        prediction_type: Optional[PredictionType] = None,
    ) -> list[ThreatPrediction]:
        """Get all predictions with pagination and optional filtering."""
        try:
            query = self.client.table("predictions").select("*")

            if prediction_type:
                query = query.eq("prediction_type", prediction_type.value)

            result = (
                query.order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            return [self._row_to_prediction(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get predictions: %s", str(e))
            return []

    async def get_high_confidence(
        self,
        min_confidence: float = 0.7,
        limit: int = 20,
    ) -> list[ThreatPrediction]:
        """Get high-confidence predictions."""
        try:
            result = (
                self.client.table("predictions")
                .select("*")
                .gte("confidence", min_confidence)
                .order("confidence", desc=True)
                .limit(limit)
                .execute()
            )

            return [self._row_to_prediction(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get high-confidence predictions: %s", str(e))
            return []

    async def get_active(self, limit: int = 50) -> list[ThreatPrediction]:
        """Get predictions that haven't expired yet."""
        try:
            now = datetime.utcnow().isoformat()
            result = (
                self.client.table("predictions")
                .select("*")
                .or_(f"expires_at.is.null,expires_at.gt.{now}")
                .order("confidence", desc=True)
                .limit(limit)
                .execute()
            )

            return [self._row_to_prediction(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get active predictions: %s", str(e))
            return []

    async def delete(self, prediction_id: str) -> bool:
        """Delete a prediction by ID."""
        try:
            result = (
                self.client.table("predictions")
                .delete()
                .eq("prediction_id", prediction_id)
                .execute()
            )
            logger.info("Deleted prediction: %s", prediction_id)
            return True
        except Exception as e:
            logger.error("Failed to delete prediction %s: %s", prediction_id, str(e))
            return False

    async def delete_by_article_id(self, article_id: str) -> int:
        """Delete all predictions for an article. Returns count deleted."""
        try:
            result = (
                self.client.table("predictions")
                .delete()
                .eq("article_id", article_id)
                .execute()
            )
            count = len(result.data) if result.data else 0
            logger.info("Deleted %d predictions for article %s", count, article_id)
            return count
        except Exception as e:
            logger.error(
                "Failed to delete predictions for article %s: %s", article_id, str(e)
            )
            return 0

    async def get_count(self) -> int:
        """Get total count of predictions."""
        try:
            result = (
                self.client.table("predictions")
                .select("prediction_id", count="exact")
                .execute()
            )
            return result.count or 0
        except Exception as e:
            logger.error("Failed to get prediction count: %s", str(e))
            return 0

    def _row_to_prediction(self, row: dict) -> ThreatPrediction:
        """Convert a database row to a ThreatPrediction model."""
        expires_at = None
        if row.get("expires_at"):
            expires_at = datetime.fromisoformat(
                row["expires_at"].replace("Z", "+00:00")
            )

        return ThreatPrediction(
            prediction_id=row["prediction_id"],
            article_id=row["article_id"],
            prediction_type=PredictionType(row["prediction_type"]),
            description=row["description"],
            confidence=row["confidence"],
            timeframe_days=row["timeframe_days"],
            reasoning=row.get("reasoning", ""),
            supporting_evidence=row.get("supporting_evidence", []),
            generated_at=datetime.fromisoformat(
                row["created_at"].replace("Z", "+00:00")
            ),
            expires_at=expires_at,
        )
