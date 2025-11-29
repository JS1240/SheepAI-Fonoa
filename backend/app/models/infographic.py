"""Infographic data models for AI-generated visual content."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class InfographicType(str, Enum):
    """Types of infographics that can be generated."""

    THREAT_SUMMARY = "threat_summary"
    TIMELINE = "timeline"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class InfographicStatus(str, Enum):
    """Status of infographic generation."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Infographic(BaseModel):
    """An AI-generated infographic for an article."""

    id: str = Field(..., description="Unique infographic identifier")
    article_id: str = Field(..., description="Source article ID")
    infographic_type: InfographicType

    # Status
    status: InfographicStatus = Field(default=InfographicStatus.PENDING)

    # Storage
    storage_path: Optional[str] = Field(
        default=None,
        description="Path in Supabase Storage bucket",
    )
    public_url: Optional[str] = Field(
        default=None,
        description="Public URL to access the infographic",
    )

    # Metadata
    prompt_used: Optional[str] = Field(
        default=None,
        description="The prompt sent to Gemini API",
    )
    generation_time_ms: Optional[int] = Field(
        default=None,
        description="Time taken to generate in milliseconds",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if generation failed",
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "infographic-a1b2c3d4",
                "article_id": "thn-2025-001",
                "infographic_type": "threat_summary",
                "status": "completed",
                "storage_path": "infographics/thn-2025-001/threat_summary.png",
                "public_url": "https://xyz.supabase.co/storage/v1/object/public/infographics/...",
                "generation_time_ms": 3500,
                "created_at": "2025-01-15T10:30:00Z",
                "completed_at": "2025-01-15T10:30:03Z",
            }
        }


class InfographicRequest(BaseModel):
    """Request to generate an infographic."""

    infographic_type: InfographicType = Field(
        default=InfographicType.THREAT_SUMMARY,
    )
    force_regenerate: bool = Field(
        default=False,
        description="Force regeneration even if one exists",
    )


class InfographicResponse(BaseModel):
    """Response containing infographic data."""

    infographic: Infographic
    is_cached: bool = Field(
        default=False,
        description="Whether this was returned from cache",
    )
