"""Prediction engine service for threat forecasting."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional

from openai import AsyncOpenAI

from app.config import settings
from app.db.repositories import PredictionRepository
from app.models.article import Article
from app.models.prediction import (
    DNAMatch,
    HourlyForecastEntry,
    PredictionType,
    ThreatDNA,
    ThreatForecast,
    ThreatPrediction,
)

if TYPE_CHECKING:
    from app.services.graph import GraphService

logger = logging.getLogger(__name__)


class PredictionService:
    """Service for generating threat predictions."""

    def __init__(self, prediction_repo: Optional[PredictionRepository] = None) -> None:
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.llm_model = settings.openai_model
        self._predictions_cache: dict[str, list[ThreatPrediction]] = {}
        self._prediction_repo = prediction_repo or PredictionRepository()

    async def generate_prediction(
        self,
        article: Article,
        prediction_type: PredictionType = PredictionType.EXPLOIT_LIKELIHOOD,
        graph_service: Optional["GraphService"] = None,
    ) -> Optional[ThreatPrediction]:
        """Generate a prediction for an article with optional graph intelligence."""
        cache_key = f"{article.id}_{prediction_type.value}"
        if cache_key in self._predictions_cache:
            predictions = self._predictions_cache[cache_key]
            if predictions:
                return predictions[0]

        # Check database for existing prediction
        existing = await self._prediction_repo.get_by_article_id(article.id)
        for pred in existing:
            if pred.prediction_type == prediction_type:
                self._predictions_cache[cache_key] = [pred]
                return pred

        # Fetch graph context for enhanced predictions
        graph_context: Optional[dict[str, Any]] = None
        if graph_service:
            graph_context = graph_service.get_prediction_context(article.id)
            if graph_context and graph_context.get("has_graph_data"):
                logger.info(
                    "Using graph context for prediction: %d connections, %d CVEs, %d actors",
                    graph_context.get("connection_count", 0),
                    len(graph_context.get("related_cves", [])),
                    len(graph_context.get("related_threat_actors", [])),
                )

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_prediction_prompt(prediction_type, graph_context),
                    },
                    {
                        "role": "user",
                        "content": self._format_article_for_prediction(article, graph_context),
                    },
                ],
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            import json

            result = json.loads(response.choices[0].message.content)

            # Get base confidence from LLM
            base_confidence = min(1.0, max(0.0, result.get("confidence", 0.5)))

            # Adjust confidence based on graph signals
            adjusted_confidence = self._adjust_confidence_with_graph(
                base_confidence, graph_context
            )

            prediction = ThreatPrediction(
                prediction_id=f"pred-{uuid.uuid4().hex[:8]}",
                article_id=article.id,
                prediction_type=prediction_type,
                description=result.get("prediction", ""),
                confidence=adjusted_confidence,
                timeframe_days=result.get("timeframe_days", 14),
                reasoning=result.get("reasoning", ""),
                supporting_evidence=result.get("supporting_evidence", []),
                expires_at=datetime.utcnow() + timedelta(
                    days=result.get("timeframe_days", 14)
                ),
            )

            # Save to database
            try:
                await self._prediction_repo.create(prediction)
            except Exception as db_err:
                logger.warning("Failed to save prediction to DB: %s", db_err)

            self._predictions_cache[cache_key] = [prediction]
            logger.info(
                "Generated prediction for %s: %s (%.0f%% confidence, graph-enhanced: %s)",
                article.id,
                prediction.description[:50],
                prediction.confidence * 100,
                "yes" if graph_context and graph_context.get("has_graph_data") else "no",
            )

            return prediction

        except Exception as e:
            logger.error("Failed to generate prediction: %s", e)
            return self._generate_fallback_prediction(article, prediction_type, graph_context)

    def _get_prediction_prompt(
        self,
        prediction_type: PredictionType,
        graph_context: Optional[dict] = None,
    ) -> str:
        """Get the graph-enhanced system prompt for a prediction type."""
        # Build graph intelligence section if available
        graph_insight = ""
        if graph_context and graph_context.get("has_graph_data"):
            connections = graph_context.get("connection_count", 0)
            if connections > 5:
                graph_insight = (
                    f"\n\nKNOWLEDGE GRAPH INTELLIGENCE: This threat has {connections} "
                    "connections in our intelligence graph, indicating significant relevance.\n"
                )
            elif connections > 0:
                graph_insight = (
                    f"\n\nKNOWLEDGE GRAPH INTELLIGENCE: This threat has {connections} "
                    "tracked connections.\n"
                )

            # Add threat actor history
            for actor in graph_context.get("threat_actor_history", []):
                if actor.get("active_campaigns"):
                    graph_insight += (
                        f"- ACTIVE CAMPAIGN: Threat actor '{actor['actor']}' appears in "
                        f"{actor['article_count']} articles - active campaign indicator.\n"
                    )

            # Add CVE trending info
            for cve in graph_context.get("cve_severity_context", []):
                if cve.get("is_trending"):
                    graph_insight += (
                        f"- TRENDING: {cve['cve']} mentioned in {cve['article_count']} "
                        "articles - escalating attention.\n"
                    )

            # Add related articles count
            related = graph_context.get("related_articles", [])
            if related:
                graph_insight += f"- STORY MOMENTUM: {len(related)} related articles tracking this threat.\n"

        base_prompt = f"""You are an elite cybersecurity threat intelligence analyst with 15+ years of experience at a leading threat intelligence firm. Your predictions are known for being BOLD, SPECIFIC, and ACCURATE.

Your task: Generate a prediction that sounds like a professional threat brief to a CISO.

CRITICAL INSTRUCTIONS:
1. Be SPECIFIC - not "may be exploited" but "exploit kits will target within 72 hours"
2. Be CONFIDENT - if evidence is strong, confidence should be 0.80+ (don't undersell obvious threats)
3. Use SPECIFIC timeframes calculated from threat severity (not generic 14 days)
4. Reference SPECIFIC technical details that demonstrate deep analysis
5. Sound like an expert, not a cautious AI
{graph_insight}
Return a JSON object with:
- prediction: Bold, specific statement (e.g., "LockBit ransomware group will weaponize CVE-2025-1234 for enterprise targeting")
- confidence: 0.0-1.0 (BE CONFIDENT when evidence supports it - 0.85+ for critical threats with active indicators)
- timeframe_days: Calculated based on threat severity (3-7 for critical, 7-14 for high, 14-30 for moderate)
- reasoning: Expert-level explanation with specific indicators (2-3 sentences)
- supporting_evidence: List of 3-5 concrete factors (CVE severity, actor history, PoC availability, graph connections)
"""

        type_prompts = {
            PredictionType.EXPLOIT_LIKELIHOOD: """
PREDICTION TYPE: Exploitation Likelihood Analysis

Key factors to weigh:
- CVSS score and attack complexity (low complexity = faster exploitation)
- Proof-of-concept availability (PoC = 10x faster exploitation)
- Threat actor interest (connected actors = active targeting likely)
- Product ubiquity (Apache, Microsoft, Linux = massive attack surface)
- Historical patterns (similar CVEs typically exploited within X days)

CONFIDENCE CALIBRATION:
- 90%+: Critical CVE + PoC available + known actor interest + actively exploited
- 80-89%: Critical CVE + active discussions OR PoC imminent
- 70-79%: High severity CVE with wide attack surface
- 60-69%: Moderate vulnerability with known interest
- Below 60%: Theoretical or limited scope only

TIMEFRAME CALIBRATION:
- 1-3 days: PoC available + active exploitation
- 3-7 days: Critical + PoC or imminent weaponization
- 7-14 days: High severity with interest
- 14-30 days: Moderate with some indicators

Output prediction like: "Active exploitation by [specific actor/type] targeting [specific systems] within [X] days"
""",

            PredictionType.SPREAD_FORECAST: """
PREDICTION TYPE: Threat Spread Forecast

Analyze:
- Target industries (finance, healthcare, government, critical infrastructure = high value)
- Attack vector scalability (supply chain = global, targeted = limited)
- Threat actor resources (nation-state = global reach, criminal = opportunistic spread)
- Defensive posture of typical targets (legacy systems = faster spread)
- Time-to-spread for similar historical threats

CONFIDENCE CALIBRATION:
- 85%+: Supply chain attack + multiple confirmed victims + active campaign
- 70-84%: Widespread vulnerability + active exploitation
- 50-69%: Targeted campaign with expansion potential

Output prediction like: "Expect targeting of [specific sectors] in [specific regions] affecting [X organizations] within [Y] days"
""",

            PredictionType.PATCH_TIMELINE: """
PREDICTION TYPE: Patch/Mitigation Timeline

Analyze:
- Vendor track record (Microsoft = 30d avg, Apple = 14d, open source varies wildly)
- CVE severity (critical = emergency patch likely within 7d)
- Active exploitation (in-the-wild = emergency response triggered)
- Patch complexity (architectural = months, simple = days)
- Workaround availability (mitigations can delay patching pressure)

CONFIDENCE CALIBRATION:
- 85%+: Major vendor + critical CVE + active exploitation
- 70-84%: Clear vendor responsibility + high severity
- 50-69%: Complex fix or unclear ownership

Output prediction like: "Vendor patch expected within [X] days, enterprise adoption reaching 50% within [Y] days"
""",

            PredictionType.ATTACK_ESCALATION: """
PREDICTION TYPE: Attack Escalation Analysis

Analyze:
- Vulnerability chain potential (initial access + privilege escalation = RCE chain)
- Threat actor sophistication (APT will chain, commodity malware exploits as-is)
- Target value (financial data, IP, infrastructure = escalation likely)
- Current attack stage (initial access -> lateral movement -> data exfiltration)
- Historical escalation patterns for this threat actor/type

CONFIDENCE CALIBRATION:
- 85%+: Active campaign + sophisticated actor + high-value targets
- 70-84%: Known escalation patterns + valuable targets
- 50-69%: Potential for escalation but limited indicators

Output prediction like: "High probability of escalation to [specific attack type] targeting [specific assets/data] resulting in [impact]"
""",
        }

        return base_prompt + type_prompts.get(prediction_type, "")

    def _format_article_for_prediction(
        self,
        article: Article,
        graph_context: Optional[dict] = None,
    ) -> str:
        """Format article with graph-enhanced context for prediction."""
        parts = [
            f"Title: {article.title}",
            f"Published: {article.published_at.isoformat()}",
        ]

        if article.summary:
            parts.append(f"Summary: {article.summary}")
        else:
            parts.append(f"Content: {article.content[:1500]}")

        if article.categories:
            parts.append(f"Categories: {', '.join(article.categories)}")

        if article.vulnerabilities:
            parts.append(f"CVEs mentioned: {', '.join(article.vulnerabilities)}")

        if article.threat_actors:
            parts.append(f"Threat actors: {', '.join(article.threat_actors)}")

        # Add graph intelligence context
        if graph_context and graph_context.get("has_graph_data"):
            parts.append("\n--- INTELLIGENCE GRAPH CONTEXT ---")

            # Connection density signals significance
            density = graph_context.get("connection_density", 0)
            if density > 0.5:
                parts.append("Graph Significance: HIGH (well-connected in threat landscape)")
            elif density > 0.2:
                parts.append("Graph Significance: MODERATE (emerging threat pattern)")
            elif density > 0:
                parts.append("Graph Significance: LOW (limited connections)")

            # Related articles indicate story momentum
            related = graph_context.get("related_articles", [])
            if related:
                parts.append(f"Related Stories: {len(related)} articles tracking this threat")
                for rel in related[:3]:  # Top 3
                    title = rel.get("title", "")[:60]
                    parts.append(f"  - {title}...")

            # Threat actor history is highly predictive
            for actor in graph_context.get("threat_actor_history", []):
                if actor.get("active_campaigns"):
                    parts.append(
                        f"THREAT ACTOR INTEL: {actor['actor']} has {actor['article_count']} "
                        "linked articles (ACTIVE CAMPAIGN INDICATOR)"
                    )
                elif actor.get("article_count", 0) > 0:
                    parts.append(
                        f"Threat Actor: {actor['actor']} ({actor['article_count']} linked articles)"
                    )

            # CVE trending indicates urgency
            for cve in graph_context.get("cve_severity_context", []):
                if cve.get("is_trending"):
                    parts.append(
                        f"CVE TRENDING: {cve['cve']} mentioned in {cve['article_count']} "
                        "articles (ESCALATING ATTENTION)"
                    )
                elif cve.get("article_count", 0) > 1:
                    parts.append(
                        f"CVE Context: {cve['cve']} ({cve['article_count']} articles)"
                    )

        return "\n".join(parts)

    def _adjust_confidence_with_graph(
        self,
        base_confidence: float,
        graph_context: Optional[dict[str, Any]],
    ) -> float:
        """Adjust confidence score based on graph intelligence signals.

        Graph signals that increase confidence:
        - High connection density indicates well-tracked threat
        - Active threat actor campaigns are strong predictors
        - Trending CVEs indicate escalating attention
        - Related articles show story momentum
        """
        if not graph_context or not graph_context.get("has_graph_data"):
            return base_confidence

        confidence = base_confidence

        # Connection density boost (up to +10%)
        density = graph_context.get("connection_density", 0)
        if density > 0.5:
            confidence += 0.10
        elif density > 0.2:
            confidence += 0.05

        # Active threat actor boost (+5% per active actor, max +15%)
        actor_boost = 0.0
        for actor in graph_context.get("threat_actor_history", []):
            if actor.get("active_campaigns"):
                actor_boost += 0.05
        confidence += min(0.15, actor_boost)

        # Trending CVE boost (+7% per trending CVE, max +14%)
        cve_boost = 0.0
        for cve in graph_context.get("cve_severity_context", []):
            if cve.get("is_trending"):
                cve_boost += 0.07
        confidence += min(0.14, cve_boost)

        # Related articles boost (story momentum)
        related_count = len(graph_context.get("related_articles", []))
        if related_count > 5:
            confidence += 0.10
        elif related_count > 2:
            confidence += 0.05

        # Cap at 95% maximum confidence
        return min(0.95, confidence)

    def _generate_fallback_prediction(
        self,
        article: Article,
        prediction_type: PredictionType,
        graph_context: Optional[dict[str, Any]] = None,
    ) -> ThreatPrediction:
        """Generate a fallback prediction when LLM fails."""
        # Use heuristics based on article content
        content_lower = article.content.lower()
        title_lower = article.title.lower()

        # Estimate severity and confidence
        confidence = 0.5
        timeframe = 14

        if "critical" in content_lower or "critical" in title_lower:
            confidence += 0.15
            timeframe = 7
        if "actively exploited" in content_lower:
            confidence += 0.2
            timeframe = 3
        if "poc" in content_lower or "proof of concept" in content_lower:
            confidence += 0.1
            timeframe = 10
        if article.vulnerabilities:
            confidence += 0.05

        # Apply graph-based confidence adjustment
        confidence = self._adjust_confidence_with_graph(confidence, graph_context)

        # Raise cap when graph supports it (0.92 vs 0.85)
        max_confidence = 0.92 if graph_context and graph_context.get("has_graph_data") else 0.85
        confidence = min(max_confidence, confidence)

        # Generate prediction-type-specific descriptions
        description_map = {
            PredictionType.EXPLOIT_LIKELIHOOD: self._get_exploit_description(article, graph_context),
            PredictionType.SPREAD_FORECAST: self._get_spread_description(article, graph_context),
            PredictionType.PATCH_TIMELINE: self._get_patch_description(article, graph_context),
            PredictionType.ATTACK_ESCALATION: self._get_escalation_description(article, graph_context),
        }

        # Build reasoning with graph context
        reasoning = "Based on severity indicators and historical patterns"
        if graph_context and graph_context.get("has_graph_data"):
            reasoning_parts = [reasoning]
            if graph_context.get("related_threat_actors"):
                reasoning_parts.append(
                    f"linked to threat actors: {', '.join(graph_context['related_threat_actors'][:2])}"
                )
            if graph_context.get("related_cves"):
                reasoning_parts.append(
                    f"connected to CVEs: {', '.join(graph_context['related_cves'][:2])}"
                )
            reasoning = "; ".join(reasoning_parts)

        return ThreatPrediction(
            prediction_id=f"pred-fallback-{uuid.uuid4().hex[:8]}",
            article_id=article.id,
            prediction_type=prediction_type,
            description=description_map.get(prediction_type, "further developments"),
            confidence=confidence,
            timeframe_days=timeframe,
            reasoning=reasoning,
            supporting_evidence=article.categories[:3],
        )

    def _get_exploit_description(
        self,
        article: Article,
        graph_context: Optional[dict[str, Any]],
    ) -> str:
        """Generate exploit likelihood description."""
        if graph_context and graph_context.get("related_cves"):
            cve = graph_context["related_cves"][0]
            return f"active exploitation targeting {cve}"
        if article.vulnerabilities:
            return f"active exploitation targeting {article.vulnerabilities[0]}"
        return "active exploitation attempts against this vulnerability"

    def _get_spread_description(
        self,
        article: Article,
        graph_context: Optional[dict[str, Any]],
    ) -> str:
        """Generate spread forecast description."""
        if graph_context and graph_context.get("related_threat_actors"):
            actor = graph_context["related_threat_actors"][0]
            return f"widespread targeting by {actor} across enterprise networks"
        return "widespread targeting across multiple sectors"

    def _get_patch_description(
        self,
        article: Article,
        graph_context: Optional[dict[str, Any]],
    ) -> str:
        """Generate patch timeline description."""
        if article.vulnerabilities:
            return f"vendor patch for {article.vulnerabilities[0]} expected"
        return "vendor patches being released"

    def _get_escalation_description(
        self,
        article: Article,
        graph_context: Optional[dict[str, Any]],
    ) -> str:
        """Generate attack escalation description."""
        if graph_context and graph_context.get("related_threat_actors"):
            return "escalation to ransomware deployment or data exfiltration"
        return "escalation to more sophisticated attacks"

    async def get_predictions_for_article(
        self,
        article: Article,
        types: Optional[list[PredictionType]] = None,
        graph_service: Optional["GraphService"] = None,
    ) -> list[ThreatPrediction]:
        """Get all predictions for an article with optional graph intelligence."""
        if types is None:
            types = [PredictionType.EXPLOIT_LIKELIHOOD]

        predictions = []
        for pred_type in types:
            prediction = await self.generate_prediction(
                article, pred_type, graph_service=graph_service
            )
            if prediction:
                predictions.append(prediction)

        return predictions


    async def generate_48_hour_forecast(
        self,
        article: Article,
        graph_service: Optional["GraphService"] = None,
    ) -> ThreatForecast:
        """Generate a 48-hour threat forecast with hourly risk progression.

        This creates a timeline visualization showing how threat risk is expected
        to evolve over the next 48 hours.
        """
        # Get graph context for enhanced forecasting
        graph_context: Optional[dict[str, Any]] = None
        if graph_service:
            graph_context = graph_service.get_prediction_context(article.id)

        # Extract threat name from article
        threat_name = self._extract_threat_name(article)

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_forecast_prompt(graph_context),
                    },
                    {
                        "role": "user",
                        "content": self._format_article_for_forecast(article, graph_context),
                    },
                ],
                max_tokens=1500,
                temperature=0.4,
                response_format={"type": "json_object"},
            )

            import json

            result = json.loads(response.choices[0].message.content)

            # Build hourly entries from LLM response
            entries = []
            now = datetime.utcnow()
            hourly_data = result.get("hourly_forecast", [])

            for entry_data in hourly_data[:48]:  # Max 48 hours
                hour = entry_data.get("hour", len(entries))
                risk_level = min(1.0, max(0.0, entry_data.get("risk_level", 0.5)))

                entries.append(
                    HourlyForecastEntry(
                        hour=hour,
                        timestamp=now + timedelta(hours=hour),
                        risk_level=risk_level,
                        risk_label=self._get_risk_label(risk_level),
                        event_description=entry_data.get("event"),
                        contributing_factors=entry_data.get("factors", []),
                    )
                )

            # If LLM didn't provide enough entries, generate remaining with interpolation
            entries = self._ensure_48_entries(entries, now)

            # Find peak risk
            peak_entry = max(entries, key=lambda e: e.risk_level)

            forecast = ThreatForecast(
                forecast_id=f"forecast-{uuid.uuid4().hex[:8]}",
                article_id=article.id,
                threat_name=threat_name,
                entries=entries,
                peak_risk_hour=peak_entry.hour,
                peak_risk_level=peak_entry.risk_level,
                summary=result.get("summary", "48-hour threat forecast generated."),
                key_milestones=result.get("milestones", []),
                recommended_actions=result.get("actions", []),
                confidence=min(1.0, max(0.0, result.get("confidence", 0.7))),
            )

            logger.info(
                "Generated 48-hour forecast for %s: peak risk %.0f%% at hour %d",
                article.id,
                forecast.peak_risk_level * 100,
                forecast.peak_risk_hour,
            )

            return forecast

        except Exception as e:
            logger.error("Failed to generate 48-hour forecast: %s", e)
            return self._generate_fallback_forecast(article, threat_name)

    def _get_forecast_prompt(self, graph_context: Optional[dict] = None) -> str:
        """Get the system prompt for 48-hour forecast generation."""
        graph_insight = ""
        if graph_context and graph_context.get("has_graph_data"):
            connections = graph_context.get("connection_count", 0)
            graph_insight = f"\n\nINTELLIGENCE CONTEXT: This threat has {connections} connections in the knowledge graph.\n"

        return f"""You are a threat intelligence analyst creating a 48-hour threat forecast.

Your task is to predict how a security threat will evolve hour-by-hour over the next 48 hours.
{graph_insight}
CRITICAL INSTRUCTIONS:
1. Create a REALISTIC progression - risk typically doesn't jump dramatically between hours
2. Identify KEY MILESTONES (e.g., "Hour 6: PoC likely released", "Hour 24: First exploitation attempts")
3. Risk should reflect BUSINESS HOURS patterns (higher during US business hours for enterprise threats)
4. Consider THREAT ACTOR timezones and typical activity patterns

Return a JSON object with:
- hourly_forecast: Array of objects with:
  - hour: 0-48 (0 = now)
  - risk_level: 0.0-1.0 (current risk level)
  - event: Brief description if something significant expected (null if quiet hour)
  - factors: List of 1-3 contributing factors
- summary: 2-3 sentence executive summary of the 48-hour outlook
- milestones: List of 3-5 key predicted events with timing
- actions: List of 3-5 recommended actions based on forecast
- confidence: 0.0-1.0 overall forecast confidence

RISK LEVELS:
- 0.0-0.2: SAFE - Normal baseline, no immediate concern
- 0.2-0.4: LOW - Monitoring recommended
- 0.4-0.6: MODERATE - Preparation advised
- 0.6-0.8: HIGH - Active response needed
- 0.8-1.0: CRITICAL - Immediate action required

Provide forecast for hours: 0, 3, 6, 9, 12, 18, 24, 30, 36, 42, 48 (11 key points minimum)
"""

    def _format_article_for_forecast(
        self,
        article: Article,
        graph_context: Optional[dict] = None,
    ) -> str:
        """Format article for forecast generation."""
        parts = [
            f"THREAT: {article.title}",
            f"Published: {article.published_at.isoformat()}",
            f"Time since publication: {(datetime.utcnow() - article.published_at).total_seconds() / 3600:.1f} hours",
        ]

        if article.summary:
            parts.append(f"Summary: {article.summary}")
        else:
            parts.append(f"Details: {article.content[:1000]}")

        if article.vulnerabilities:
            parts.append(f"CVEs: {', '.join(article.vulnerabilities)}")

        if article.threat_actors:
            parts.append(f"Threat Actors: {', '.join(article.threat_actors)}")

        if article.categories:
            parts.append(f"Categories: {', '.join(article.categories)}")

        if graph_context and graph_context.get("has_graph_data"):
            parts.append("\n--- GRAPH INTELLIGENCE ---")
            for actor in graph_context.get("threat_actor_history", []):
                if actor.get("active_campaigns"):
                    parts.append(f"ACTIVE CAMPAIGN: {actor['actor']}")
            for cve in graph_context.get("cve_severity_context", []):
                if cve.get("is_trending"):
                    parts.append(f"TRENDING CVE: {cve['cve']}")

        return "\n".join(parts)

    def _extract_threat_name(self, article: Article) -> str:
        """Extract a concise threat name from the article."""
        if article.vulnerabilities:
            return article.vulnerabilities[0]
        if article.threat_actors:
            return article.threat_actors[0]
        # Extract from title - take first 40 chars before any colon or dash
        title = article.title
        for sep in [":", " - ", " | "]:
            if sep in title:
                title = title.split(sep)[0]
        return title[:40].strip()

    def _get_risk_label(self, risk_level: float) -> str:
        """Convert risk level to human-readable label."""
        if risk_level >= 0.8:
            return "CRITICAL"
        elif risk_level >= 0.6:
            return "HIGH"
        elif risk_level >= 0.4:
            return "MODERATE"
        elif risk_level >= 0.2:
            return "LOW"
        else:
            return "SAFE"

    def _ensure_48_entries(
        self,
        entries: list[HourlyForecastEntry],
        start_time: datetime,
    ) -> list[HourlyForecastEntry]:
        """Ensure we have entries for all 48 hours through interpolation."""
        if not entries:
            # Generate baseline entries
            return self._generate_baseline_entries(start_time, 0.3)

        # Create a dict of existing entries by hour
        existing = {e.hour: e for e in entries}

        # Fill in missing hours with interpolation
        result = []
        for hour in range(49):  # 0 to 48
            if hour in existing:
                result.append(existing[hour])
            else:
                # Find nearest entries for interpolation
                prev_hour = max((h for h in existing.keys() if h < hour), default=0)
                next_hour = min((h for h in existing.keys() if h > hour), default=48)

                prev_entry = existing.get(prev_hour)
                next_entry = existing.get(next_hour)

                if prev_entry and next_entry and next_hour > prev_hour:
                    # Linear interpolation
                    ratio = (hour - prev_hour) / (next_hour - prev_hour)
                    risk = prev_entry.risk_level + ratio * (next_entry.risk_level - prev_entry.risk_level)
                elif prev_entry:
                    risk = prev_entry.risk_level
                elif next_entry:
                    risk = next_entry.risk_level
                else:
                    risk = 0.3

                result.append(
                    HourlyForecastEntry(
                        hour=hour,
                        timestamp=start_time + timedelta(hours=hour),
                        risk_level=risk,
                        risk_label=self._get_risk_label(risk),
                        event_description=None,
                        contributing_factors=[],
                    )
                )

        return result

    def _generate_baseline_entries(
        self,
        start_time: datetime,
        base_risk: float,
    ) -> list[HourlyForecastEntry]:
        """Generate baseline forecast entries when LLM fails."""
        entries = []
        for hour in range(49):
            # Add some variation based on business hours
            hour_of_day = (start_time + timedelta(hours=hour)).hour
            if 9 <= hour_of_day <= 17:  # Business hours
                risk = base_risk + 0.1
            else:
                risk = base_risk - 0.05

            # Gradually increase risk over 48 hours
            risk += (hour / 48) * 0.2
            risk = min(0.9, max(0.1, risk))

            entries.append(
                HourlyForecastEntry(
                    hour=hour,
                    timestamp=start_time + timedelta(hours=hour),
                    risk_level=risk,
                    risk_label=self._get_risk_label(risk),
                    event_description=None,
                    contributing_factors=[],
                )
            )

        return entries

    def _generate_fallback_forecast(
        self,
        article: Article,
        threat_name: str,
    ) -> ThreatForecast:
        """Generate a fallback forecast when LLM fails."""
        now = datetime.utcnow()

        # Determine base risk from article content
        content_lower = article.content.lower()
        base_risk = 0.4

        if "critical" in content_lower:
            base_risk = 0.6
        if "actively exploited" in content_lower:
            base_risk = 0.7
        if article.vulnerabilities:
            base_risk += 0.1

        entries = self._generate_baseline_entries(now, base_risk)
        peak_entry = max(entries, key=lambda e: e.risk_level)

        return ThreatForecast(
            forecast_id=f"forecast-fallback-{uuid.uuid4().hex[:8]}",
            article_id=article.id,
            threat_name=threat_name,
            entries=entries,
            peak_risk_hour=peak_entry.hour,
            peak_risk_level=peak_entry.risk_level,
            summary=f"48-hour forecast for {threat_name}. Risk expected to increase over time.",
            key_milestones=[
                "Hour 0: Initial threat detected",
                f"Hour {peak_entry.hour}: Peak risk anticipated",
                "Hour 48: Continued monitoring recommended",
            ],
            recommended_actions=[
                "Monitor threat intelligence feeds",
                "Verify patch status for affected systems",
                "Prepare incident response team",
            ],
            confidence=0.6,
        )


    async def generate_threat_dna(
        self,
        article: Article,
        graph_service: Optional["GraphService"] = None,
    ) -> ThreatDNA:
        """Generate threat DNA analysis with historical pattern matching.

        This identifies how the current threat relates to historical threats
        by analyzing shared characteristics, attack patterns, and outcomes.
        """
        # Get graph context for enhanced matching
        graph_context: Optional[dict[str, Any]] = None
        if graph_service:
            graph_context = graph_service.get_prediction_context(article.id)

        threat_name = self._extract_threat_name(article)

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_dna_prompt(graph_context),
                    },
                    {
                        "role": "user",
                        "content": self._format_article_for_dna(article, graph_context),
                    },
                ],
                max_tokens=1500,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            import json

            result = json.loads(response.choices[0].message.content)

            # Build DNA matches from LLM response
            matches = []
            for match_data in result.get("historical_matches", [])[:5]:
                matches.append(
                    DNAMatch(
                        match_id=f"match-{uuid.uuid4().hex[:8]}",
                        historical_article_id=match_data.get("article_id", f"hist-{uuid.uuid4().hex[:6]}"),
                        historical_title=match_data.get("title", "Historical Threat"),
                        historical_date=datetime.utcnow() - timedelta(days=match_data.get("days_ago", 90)),
                        similarity_score=min(1.0, max(0.0, match_data.get("similarity", 0.7))),
                        matching_attributes=match_data.get("attributes", []),
                        shared_threat_actors=match_data.get("threat_actors", []),
                        shared_vulnerabilities=match_data.get("vulnerabilities", []),
                        shared_techniques=match_data.get("techniques", []),
                        historical_outcome=match_data.get("outcome", ""),
                        lessons_learned=match_data.get("lessons", []),
                    )
                )

            dna = ThreatDNA(
                dna_id=f"dna-{uuid.uuid4().hex[:8]}",
                article_id=article.id,
                threat_name=threat_name,
                threat_type=result.get("threat_type", ""),
                attack_vector=result.get("attack_vector", ""),
                target_sectors=result.get("target_sectors", []),
                indicators=result.get("indicators", []),
                techniques=result.get("techniques", []),
                matches=matches,
                summary=result.get("summary", ""),
                risk_assessment=result.get("risk_assessment", ""),
                recommended_defenses=result.get("defenses", []),
                confidence=min(1.0, max(0.0, result.get("confidence", 0.7))),
            )

            logger.info(
                "Generated threat DNA for %s: %d matches, top score %.0f%%",
                article.id,
                len(matches),
                dna.top_match_score * 100,
            )

            return dna

        except Exception as e:
            logger.error("Failed to generate threat DNA: %s", e)
            return self._generate_fallback_dna(article, threat_name)

    def _get_dna_prompt(self, graph_context: Optional[dict] = None) -> str:
        """Get the system prompt for threat DNA analysis."""
        graph_insight = ""
        if graph_context and graph_context.get("has_graph_data"):
            connections = graph_context.get("connection_count", 0)
            graph_insight = f"\n\nKNOWLEDGE GRAPH: This threat has {connections} connections in our intelligence database.\n"

        return f"""You are a threat intelligence analyst performing THREAT DNA MATCHING.

Your task is to identify how the current threat relates to historical threats by finding pattern matches.
{graph_insight}
CRITICAL INSTRUCTIONS:
1. Identify 2-5 HISTORICAL THREATS that share characteristics with this threat
2. For each match, provide SPECIFIC similarities (same CVE type, same actor, same technique)
3. Include what HAPPENED with the historical threat (outcome) as a predictor
4. Extract LESSONS LEARNED that apply to defending against this threat
5. Map to MITRE ATT&CK techniques where applicable

Return a JSON object with:
- threat_type: Category (ransomware, apt, vulnerability, supply_chain, etc.)
- attack_vector: Primary attack method (phishing, exploit, supply_chain, etc.)
- target_sectors: List of targeted industries
- indicators: Key threat indicators (IoCs, TTPs)
- techniques: MITRE ATT&CK technique IDs (T1xxx format)
- historical_matches: Array of matches with:
  - title: Historical threat name
  - days_ago: How long ago (30-365)
  - similarity: 0.0-1.0 match strength
  - attributes: List of matching attributes
  - threat_actors: Shared threat actors
  - vulnerabilities: Shared CVE types
  - techniques: Shared MITRE techniques
  - outcome: What happened (exploitation, ransomware, data breach, etc.)
  - lessons: 2-3 lessons learned
- summary: Executive summary of DNA analysis
- risk_assessment: Risk assessment based on historical patterns
- defenses: 3-5 recommended defensive measures
- confidence: 0.0-1.0 analysis confidence

MATCH QUALITY CALIBRATION:
- 85%+: Same threat actor + same vulnerability type + similar targets
- 70-84%: Same attack vector + similar techniques + overlapping targets
- 50-69%: Similar threat type + some shared characteristics
- Below 50%: Partial match with limited similarities
"""

    def _format_article_for_dna(
        self,
        article: Article,
        graph_context: Optional[dict] = None,
    ) -> str:
        """Format article for DNA analysis."""
        parts = [
            f"CURRENT THREAT: {article.title}",
            f"Published: {article.published_at.isoformat()}",
        ]

        if article.summary:
            parts.append(f"Summary: {article.summary}")
        else:
            parts.append(f"Details: {article.content[:1200]}")

        if article.vulnerabilities:
            parts.append(f"CVEs: {', '.join(article.vulnerabilities)}")

        if article.threat_actors:
            parts.append(f"Threat Actors: {', '.join(article.threat_actors)}")

        if article.categories:
            parts.append(f"Categories: {', '.join(article.categories)}")

        if graph_context and graph_context.get("has_graph_data"):
            parts.append("\n--- INTELLIGENCE CONTEXT ---")
            for actor in graph_context.get("threat_actor_history", []):
                parts.append(f"Known Actor: {actor['actor']} ({actor.get('article_count', 0)} linked articles)")
            for cve in graph_context.get("cve_severity_context", []):
                parts.append(f"CVE Intel: {cve['cve']} ({cve.get('article_count', 0)} articles)")

        return "\n".join(parts)

    def _generate_fallback_dna(
        self,
        article: Article,
        threat_name: str,
    ) -> ThreatDNA:
        """Generate a fallback DNA analysis when LLM fails."""
        content_lower = article.content.lower()

        # Detect threat type from content
        threat_type = "vulnerability"
        if "ransomware" in content_lower:
            threat_type = "ransomware"
        elif "apt" in content_lower or "nation-state" in content_lower:
            threat_type = "apt"
        elif "supply chain" in content_lower:
            threat_type = "supply_chain"
        elif "phishing" in content_lower:
            threat_type = "phishing"

        # Detect attack vector
        attack_vector = "unknown"
        if "exploit" in content_lower:
            attack_vector = "exploit"
        elif "phishing" in content_lower:
            attack_vector = "phishing"
        elif "supply chain" in content_lower:
            attack_vector = "supply_chain"
        elif "remote code" in content_lower or "rce" in content_lower:
            attack_vector = "remote_code_execution"

        # Generate a generic historical match
        matches = [
            DNAMatch(
                match_id=f"match-fallback-{uuid.uuid4().hex[:8]}",
                historical_article_id=f"hist-{uuid.uuid4().hex[:6]}",
                historical_title=f"Similar {threat_type.replace('_', ' ').title()} Threat",
                historical_date=datetime.utcnow() - timedelta(days=90),
                similarity_score=0.65,
                matching_attributes=[threat_type, attack_vector],
                shared_threat_actors=article.threat_actors[:2] if article.threat_actors else [],
                shared_vulnerabilities=article.vulnerabilities[:2] if article.vulnerabilities else [],
                shared_techniques=["T1190", "T1059"] if attack_vector == "exploit" else ["T1566"],
                historical_outcome=f"Historical {threat_type} campaigns typically resulted in data exfiltration",
                lessons_learned=[
                    "Rapid patching reduced impact",
                    "Network segmentation limited spread",
                ],
            )
        ]

        return ThreatDNA(
            dna_id=f"dna-fallback-{uuid.uuid4().hex[:8]}",
            article_id=article.id,
            threat_name=threat_name,
            threat_type=threat_type,
            attack_vector=attack_vector,
            target_sectors=["enterprise", "government"] if threat_type == "apt" else ["general"],
            indicators=article.vulnerabilities[:3] if article.vulnerabilities else [],
            techniques=["T1190"] if attack_vector == "exploit" else ["T1566"],
            matches=matches,
            summary=f"Threat DNA analysis for {threat_name}. Pattern matching based on threat characteristics.",
            risk_assessment=f"Based on historical {threat_type} patterns, elevated risk of similar outcomes.",
            recommended_defenses=[
                "Implement recommended patches",
                "Monitor for indicators of compromise",
                "Review access controls and segmentation",
            ],
            confidence=0.6,
        )


# Singleton instance
prediction_service = PredictionService()
