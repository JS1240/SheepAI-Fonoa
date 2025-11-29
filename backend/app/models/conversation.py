"""Conversation and timeline data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.article import ArticleSummary
from app.models.graph import GraphVisualization
from app.models.prediction import ThreatPrediction


class EventType(str, Enum):
    """Types of events in a story timeline."""

    DISCLOSURE = "disclosure"
    VULNERABILITY = "vulnerability"
    EXPLOIT = "exploit"
    PATCH = "patch"
    BREACH = "breach"
    UPDATE = "update"
    ADVISORY = "advisory"


class TimelineEvent(BaseModel):
    """A single event in a story timeline."""

    event_id: str = Field(..., description="Unique event identifier")
    article_id: str = Field(..., description="Source article ID")
    title: str = Field(..., max_length=200)
    event_type: EventType
    timestamp: datetime
    severity: str = Field(
        default="medium",
        description="Event severity: critical/high/medium/low",
    )
    description: Optional[str] = Field(default=None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt-2025-001",
                "article_id": "thn-2025-001",
                "title": "Apache Struts RCE Disclosed",
                "event_type": "disclosure",
                "timestamp": "2025-01-15T10:30:00Z",
                "severity": "critical",
            }
        }


class StoryTimeline(BaseModel):
    """A complete timeline for a security story/threat evolution."""

    story_id: str = Field(..., description="Unique story identifier")
    title: str = Field(..., description="Story headline")
    events: list[TimelineEvent] = Field(default_factory=list)
    current_status: str = Field(
        default="active",
        description="Story status: active/resolved/monitoring",
    )
    prediction: Optional[ThreatPrediction] = Field(default=None)
    first_seen: Optional[datetime] = Field(default=None)
    last_updated: Optional[datetime] = Field(default=None)

    @property
    def event_count(self) -> int:
        """Return the number of events in this timeline."""
        return len(self.events)

    @property
    def duration_days(self) -> Optional[int]:
        """Return the duration of this story in days."""
        if self.first_seen and self.last_updated:
            delta = self.last_updated - self.first_seen
            return delta.days
        return None


class UserPreferences(BaseModel):
    """User preferences for personalized responses."""

    role: str = Field(default="", description="User's professional role")
    industry: str = Field(default="", description="User's industry")
    seniority: str = Field(default="", description="User's seniority level")
    interests: list[str] = Field(default_factory=list, description="Security topics of interest")
    summary_style: str = Field(
        default="technical",
        description="Preferred summary style: non-technical, technical, or executive",
    )
    detail_level: str = Field(
        default="detailed",
        description="Preferred detail level: brief, detailed, or comprehensive",
    )


class ConversationRequest(BaseModel):
    """Request from user to the chat interface."""

    message: str = Field(..., min_length=1, max_length=1000)
    user_id: Optional[str] = Field(default=None)
    context: Optional[list[str]] = Field(
        default=None,
        description="Previous message IDs for context",
    )
    include_timeline: bool = Field(default=True)
    include_graph: bool = Field(default=True)
    include_predictions: bool = Field(default=True)
    user_preferences: Optional[UserPreferences] = Field(
        default=None,
        description="User preferences for personalized responses",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Show me the latest ransomware story",
                "include_timeline": True,
                "include_graph": True,
                "include_predictions": True,
                "user_preferences": {
                    "role": "Security Analyst",
                    "industry": "Financial Services",
                    "interests": ["ransomware", "vulnerabilities"],
                    "summary_style": "technical",
                    "detail_level": "detailed",
                },
            }
        }


class ConversationResponse(BaseModel):
    """Response from the chat interface with all intelligence data."""

    response_text: str = Field(..., description="Natural language response")
    articles: list[ArticleSummary] = Field(default_factory=list)
    timeline: Optional[StoryTimeline] = Field(default=None)
    graph_data: Optional[GraphVisualization] = Field(default=None)
    predictions: list[ThreatPrediction] = Field(default_factory=list)

    # Metadata
    query_understood: bool = Field(default=True)
    suggested_followups: list[str] = Field(default_factory=list)
    processing_time_ms: Optional[int] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "response_text": "Here's the latest on ransomware threats...",
                "articles": [{"id": "thn-2025-001", "title": "..."}],
                "predictions": [
                    {
                        "description": "exploit kits targeting this",
                        "confidence": 0.73,
                        "timeframe_days": 14,
                    }
                ],
                "suggested_followups": [
                    "What vulnerabilities are connected?",
                    "Show me the threat actors involved",
                ],
            }
        }


class IntentType(str, Enum):
    """Types of user intents we can detect."""

    SHOW_LATEST = "show_latest"
    SHOW_CONNECTIONS = "show_connections"
    SHOW_EVOLUTION = "show_evolution"
    SHOW_PREDICTIONS = "show_predictions"
    SEARCH = "search"
    EXPLAIN = "explain"
    COMPARE = "compare"
    UNKNOWN = "unknown"


class AudienceType(str, Enum):
    """Target audiences for threat translation."""

    CEO = "ceo"
    BOARD = "board"
    DEVELOPERS = "developers"


class ExplainToRequest(BaseModel):
    """Request to translate threat content for a specific audience."""

    content: str = Field(..., min_length=1, max_length=5000, description="Threat content to translate")
    audience: AudienceType = Field(..., description="Target audience for translation")
    article_id: Optional[str] = Field(default=None, description="Source article ID for context")
    prediction_id: Optional[str] = Field(default=None, description="Source prediction ID for context")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Critical RCE vulnerability CVE-2025-1234 in Apache Struts allows unauthenticated remote code execution via OGNL injection.",
                "audience": "ceo",
                "article_id": "thn-2025-001",
            }
        }


class ExplainToResponse(BaseModel):
    """Response with translated threat explanation for target audience."""

    original_content: str = Field(..., description="Original technical content")
    audience: AudienceType = Field(..., description="Target audience")
    translated_content: str = Field(..., description="Audience-appropriate explanation")
    key_points: list[str] = Field(default_factory=list, description="Key takeaways for the audience")
    recommended_actions: list[str] = Field(default_factory=list, description="Suggested actions for this audience")
    risk_level: str = Field(default="medium", description="Risk level: critical/high/medium/low")
    business_impact: Optional[str] = Field(default=None, description="Business impact summary")

    class Config:
        json_schema_extra = {
            "example": {
                "original_content": "Critical RCE vulnerability...",
                "audience": "ceo",
                "translated_content": "A critical security flaw has been discovered that could allow attackers to take complete control of our web servers.",
                "key_points": [
                    "Immediate action required",
                    "All internet-facing systems potentially at risk",
                    "Patch available and should be deployed within 24 hours",
                ],
                "recommended_actions": [
                    "Authorize emergency patch deployment",
                    "Notify board of elevated risk status",
                    "Prepare customer communication if breach occurs",
                ],
                "risk_level": "critical",
                "business_impact": "Potential for complete system compromise, data breach, and regulatory penalties.",
            }
        }


class ParsedIntent(BaseModel):
    """Parsed user intent from a message."""

    intent_type: IntentType
    topic: Optional[str] = Field(default=None)
    entities: list[str] = Field(default_factory=list)
    time_range_days: Optional[int] = Field(default=None)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
