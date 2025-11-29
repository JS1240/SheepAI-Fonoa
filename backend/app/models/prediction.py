"""Prediction engine data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field


class PredictionType(str, Enum):
    """Types of threat predictions."""

    EXPLOIT_LIKELIHOOD = "exploit_likelihood"
    SPREAD_FORECAST = "spread_forecast"
    PATCH_TIMELINE = "patch_timeline"
    ATTACK_ESCALATION = "attack_escalation"


class ConfidenceLevel(str, Enum):
    """Human-readable confidence levels."""

    VERY_HIGH = "very_high"  # 85-100%
    HIGH = "high"  # 70-84%
    MODERATE = "moderate"  # 50-69%
    LOW = "low"  # 25-49%
    VERY_LOW = "very_low"  # 0-24%


class ThreatPrediction(BaseModel):
    """A prediction about threat evolution or exploitation."""

    prediction_id: str = Field(..., description="Unique prediction identifier")
    article_id: str = Field(..., description="Source article for this prediction")
    prediction_type: PredictionType

    # The prediction itself
    description: str = Field(
        ...,
        description="Human-readable prediction statement",
        max_length=500,
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0",
    )
    timeframe_days: int = Field(
        ...,
        ge=1,
        le=365,
        description="Prediction timeframe in days",
    )

    # Reasoning
    reasoning: str = Field(
        default="",
        description="Explanation of why this prediction was made",
        max_length=1000,
    )
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="Article IDs or facts supporting this prediction",
    )

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)

    @property
    def confidence_percentage(self) -> int:
        """Return confidence as a percentage integer."""
        return int(self.confidence * 100)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Return human-readable confidence level."""
        if self.confidence >= 0.85:
            return ConfidenceLevel.VERY_HIGH
        elif self.confidence >= 0.70:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.50:
            return ConfidenceLevel.MODERATE
        elif self.confidence >= 0.25:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def to_display_string(self) -> str:
        """Generate the demo-ready prediction string."""
        return (
            f"{self.confidence_percentage}% probability of "
            f"{self.description} within {self.timeframe_days} days"
        )

    def to_demo_card(self) -> dict:
        """Generate a demo-ready card format for UI display.

        Returns a dictionary optimized for compelling demo presentation:
        - headline: Bold percentage + prediction (e.g., "87% - Exploit kits targeting CVE-2025-1234")
        - timeframe: Human-readable timeframe (e.g., "Expected within 5 days")
        - urgency: CRITICAL/HIGH/MODERATE based on timeframe and confidence
        - reasoning: Expert-level explanation
        - evidence: List of supporting factors
        - confidence_level: Human-readable confidence tier
        """
        # Determine urgency based on timeframe and confidence
        if self.timeframe_days <= 5 and self.confidence >= 0.75:
            urgency = "CRITICAL"
        elif self.timeframe_days <= 10 and self.confidence >= 0.65:
            urgency = "HIGH"
        elif self.timeframe_days <= 14 and self.confidence >= 0.50:
            urgency = "MODERATE"
        else:
            urgency = "LOW"

        # Format timeframe for display
        if self.timeframe_days == 1:
            timeframe_display = "Expected within 24 hours"
        elif self.timeframe_days <= 3:
            timeframe_display = f"Expected within {self.timeframe_days} days"
        elif self.timeframe_days <= 7:
            timeframe_display = "Expected this week"
        elif self.timeframe_days <= 14:
            timeframe_display = "Expected within 2 weeks"
        elif self.timeframe_days <= 30:
            timeframe_display = "Expected this month"
        else:
            timeframe_display = f"Expected within {self.timeframe_days} days"

        # Build headline with confidence and description
        headline = f"{self.confidence_percentage}% - {self.description.capitalize()}"

        return {
            "headline": headline,
            "timeframe": timeframe_display,
            "urgency": urgency,
            "reasoning": self.reasoning,
            "evidence": self.supporting_evidence,
            "confidence_level": self.confidence_level.value,
            "prediction_type": self.prediction_type.value,
            "raw_confidence": self.confidence,
            "raw_timeframe_days": self.timeframe_days,
        }

    @computed_field
    @property
    def demo_card_data(self) -> dict[str, Any]:
        """Demo-ready card format - auto-serialized in API responses."""
        return self.to_demo_card()

    class Config:
        json_schema_extra = {
            "example": {
                "prediction_id": "pred-2025-001",
                "article_id": "thn-2025-001",
                "prediction_type": "exploit_likelihood",
                "description": "exploit kits targeting this vulnerability",
                "confidence": 0.73,
                "timeframe_days": 14,
                "reasoning": "Based on CVSS 9.8 severity and historical patterns for Apache vulnerabilities",
                "supporting_evidence": ["thn-2024-998", "thn-2024-876"],
            }
        }


class PredictionRequest(BaseModel):
    """Request to generate a prediction for an article."""

    article_id: str
    prediction_types: list[PredictionType] = Field(
        default=[PredictionType.EXPLOIT_LIKELIHOOD]
    )
    include_reasoning: bool = Field(default=True)


class DNAMatch(BaseModel):
    """A historical threat pattern match."""

    match_id: str = Field(..., description="Unique match identifier")
    historical_article_id: str = Field(..., description="ID of the historical article")
    historical_title: str = Field(..., description="Title of the historical threat")
    historical_date: datetime = Field(..., description="When the historical threat occurred")

    # Match quality
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall similarity score",
    )

    # Matching attributes
    matching_attributes: list[str] = Field(
        default_factory=list,
        description="Attributes that matched (e.g., 'threat_actor', 'vulnerability_type', 'attack_vector')",
    )
    shared_threat_actors: list[str] = Field(
        default_factory=list,
        description="Common threat actors between threats",
    )
    shared_vulnerabilities: list[str] = Field(
        default_factory=list,
        description="Common vulnerability types",
    )
    shared_techniques: list[str] = Field(
        default_factory=list,
        description="Common attack techniques (MITRE ATT&CK)",
    )

    # Historical outcome
    historical_outcome: str = Field(
        default="",
        description="What happened with the historical threat",
    )
    lessons_learned: list[str] = Field(
        default_factory=list,
        description="Key lessons from the historical case",
    )

    @computed_field
    @property
    def match_strength(self) -> str:
        """Human-readable match strength."""
        if self.similarity_score >= 0.85:
            return "STRONG"
        elif self.similarity_score >= 0.70:
            return "MODERATE"
        elif self.similarity_score >= 0.50:
            return "WEAK"
        else:
            return "PARTIAL"


class ThreatDNA(BaseModel):
    """Threat DNA analysis with historical pattern matching."""

    dna_id: str = Field(..., description="Unique DNA analysis identifier")
    article_id: str = Field(..., description="Source article for this analysis")
    threat_name: str = Field(..., description="Name of the current threat")

    # DNA Profile
    threat_type: str = Field(default="", description="Category of threat")
    attack_vector: str = Field(default="", description="Primary attack vector")
    target_sectors: list[str] = Field(default_factory=list, description="Targeted industries")
    indicators: list[str] = Field(default_factory=list, description="Key threat indicators")
    techniques: list[str] = Field(default_factory=list, description="MITRE ATT&CK techniques")

    # Historical matches
    matches: list[DNAMatch] = Field(
        default_factory=list,
        description="Historical threat pattern matches",
    )

    # Analysis summary
    summary: str = Field(
        default="",
        description="Executive summary of DNA analysis",
    )
    risk_assessment: str = Field(
        default="",
        description="Risk assessment based on historical patterns",
    )
    recommended_defenses: list[str] = Field(
        default_factory=list,
        description="Recommended defensive measures based on historical outcomes",
    )

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)

    @computed_field
    @property
    def top_match_score(self) -> float:
        """Return the highest match score."""
        if not self.matches:
            return 0.0
        return max(m.similarity_score for m in self.matches)

    @computed_field
    @property
    def has_strong_precedent(self) -> bool:
        """Check if there's a strong historical precedent."""
        return any(m.similarity_score >= 0.75 for m in self.matches)


class HourlyForecastEntry(BaseModel):
    """A single hour entry in the 48-hour forecast."""

    hour: int = Field(..., ge=0, le=48, description="Hour offset from now (0-48)")
    timestamp: datetime = Field(..., description="Actual timestamp for this hour")
    risk_level: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Risk level from 0.0 (safe) to 1.0 (critical)",
    )
    risk_label: str = Field(
        ...,
        description="Human-readable risk label (SAFE, LOW, MODERATE, HIGH, CRITICAL)",
    )
    event_description: Optional[str] = Field(
        default=None,
        description="Description of predicted event at this hour",
    )
    contributing_factors: list[str] = Field(
        default_factory=list,
        description="Factors contributing to risk level",
    )

    @property
    def risk_color(self) -> str:
        """Return color code for visualization."""
        if self.risk_level >= 0.8:
            return "#ef4444"  # red
        elif self.risk_level >= 0.6:
            return "#f97316"  # orange
        elif self.risk_level >= 0.4:
            return "#eab308"  # yellow
        elif self.risk_level >= 0.2:
            return "#22c55e"  # green
        else:
            return "#3b82f6"  # blue (safe)


class ThreatForecast(BaseModel):
    """48-hour threat forecast with hourly risk progression."""

    forecast_id: str = Field(..., description="Unique forecast identifier")
    article_id: str = Field(..., description="Source article for this forecast")
    threat_name: str = Field(..., description="Name of the threat being forecasted")

    # Forecast data
    entries: list[HourlyForecastEntry] = Field(
        default_factory=list,
        description="Hourly forecast entries (up to 48)",
    )
    peak_risk_hour: int = Field(
        default=0,
        description="Hour with highest predicted risk",
    )
    peak_risk_level: float = Field(
        default=0.0,
        description="Maximum risk level in forecast",
    )

    # Summary
    summary: str = Field(
        default="",
        description="Executive summary of the 48-hour forecast",
    )
    key_milestones: list[str] = Field(
        default_factory=list,
        description="Key predicted events in the timeline",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Actions to take based on forecast",
    )

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Overall forecast confidence",
    )

    @property
    def confidence_percentage(self) -> int:
        """Return confidence as a percentage integer."""
        return int(self.confidence * 100)

    @computed_field
    @property
    def urgency_level(self) -> str:
        """Calculate overall urgency based on peak risk and timing."""
        if self.peak_risk_level >= 0.8 and self.peak_risk_hour <= 12:
            return "CRITICAL"
        elif self.peak_risk_level >= 0.6 and self.peak_risk_hour <= 24:
            return "HIGH"
        elif self.peak_risk_level >= 0.4:
            return "MODERATE"
        else:
            return "LOW"
