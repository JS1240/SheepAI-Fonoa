"""Infographic generation service using Google Gemini API."""

import logging
import time
import uuid
from datetime import datetime
from typing import Optional

from google import genai
from google.genai import types

from app.config import settings
from app.db.supabase_client import get_supabase_client
from app.models.article import Article
from app.models.graph import GraphVisualization
from app.models.infographic import (
    Infographic,
    InfographicStatus,
    InfographicType,
)
from app.models.prediction import ThreatPrediction

logger = logging.getLogger(__name__)


class InfographicService:
    """Service for generating infographics using Gemini API."""

    def __init__(self) -> None:
        self.client: Optional[genai.Client] = None
        self.model = settings.gemini_model
        self.fallback_model = settings.gemini_fallback_model
        self.bucket_name = settings.infographic_bucket

    def _get_client(self) -> genai.Client:
        """Get or create the Gemini client."""
        if self.client is None:
            if not settings.google_api_key:
                raise ValueError("GOOGLE_API_KEY not configured")
            self.client = genai.Client(api_key=settings.google_api_key)
        return self.client

    async def generate_infographic(
        self,
        article: Article,
        infographic_type: InfographicType,
        graph: Optional[GraphVisualization] = None,
        predictions: Optional[list[ThreatPrediction]] = None,
        timeline_events: Optional[list[dict]] = None,
    ) -> Infographic:
        """Generate an infographic for an article.

        Args:
            article: The source article
            infographic_type: Type of infographic to generate
            graph: Knowledge graph data (for knowledge_graph type)
            predictions: Threat predictions (for timeline type)
            timeline_events: Timeline events (for timeline type)

        Returns:
            Generated Infographic with public URL
        """
        infographic_id = f"infographic-{uuid.uuid4().hex[:8]}"
        start_time = time.time()

        infographic = Infographic(
            id=infographic_id,
            article_id=article.id,
            infographic_type=infographic_type,
            status=InfographicStatus.GENERATING,
        )

        try:
            # Build the prompt based on type
            prompt = self._build_prompt(
                article=article,
                infographic_type=infographic_type,
                graph=graph,
                predictions=predictions,
                timeline_events=timeline_events,
            )
            infographic.prompt_used = prompt

            # Generate image with Gemini
            image_bytes = await self._generate_image(prompt)

            # Upload to Supabase Storage
            storage_path = f"{article.id}/{infographic_type.value}.png"
            public_url = await self._upload_to_storage(
                image_bytes=image_bytes,
                path=storage_path,
            )

            # Update infographic with results
            infographic.status = InfographicStatus.COMPLETED
            infographic.storage_path = storage_path
            infographic.public_url = public_url
            infographic.completed_at = datetime.utcnow()
            infographic.generation_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "Generated infographic %s for article %s in %dms",
                infographic_id,
                article.id,
                infographic.generation_time_ms,
            )

        except Exception as e:
            logger.error("Failed to generate infographic: %s", e)
            infographic.status = InfographicStatus.FAILED
            infographic.error_message = str(e)

        return infographic

    def _build_prompt(
        self,
        article: Article,
        infographic_type: InfographicType,
        graph: Optional[GraphVisualization] = None,
        predictions: Optional[list[ThreatPrediction]] = None,
        timeline_events: Optional[list[dict]] = None,
    ) -> str:
        """Build the appropriate prompt for the infographic type."""
        if infographic_type == InfographicType.THREAT_SUMMARY:
            return self._build_threat_summary_prompt(article)
        elif infographic_type == InfographicType.TIMELINE:
            return self._build_timeline_prompt(article, predictions, timeline_events)
        elif infographic_type == InfographicType.KNOWLEDGE_GRAPH:
            return self._build_knowledge_graph_prompt(article, graph)
        else:
            raise ValueError(f"Unknown infographic type: {infographic_type}")

    def _build_threat_summary_prompt(self, article: Article) -> str:
        """Build prompt for threat summary infographic."""
        vulnerabilities = (
            ", ".join(article.vulnerabilities) if article.vulnerabilities else "None identified"
        )
        threat_actors = (
            ", ".join(article.threat_actors) if article.threat_actors else "None identified"
        )
        categories = ", ".join(article.categories) if article.categories else "General Security"

        # Determine severity based on content
        content_lower = article.content.lower() if article.content else ""
        if any(term in content_lower for term in ["critical", "zero-day", "actively exploited", "rce"]):
            severity = "CRITICAL"
        elif any(term in content_lower for term in ["high severity", "important", "urgent"]):
            severity = "HIGH"
        else:
            severity = "MEDIUM"

        summary_text = article.summary[:300] if article.summary else article.content[:300]

        return f"""Create a professional cybersecurity threat summary infographic with the following design:

STYLE REQUIREMENTS:
- Dark theme with cyber/tech aesthetic (dark blue/purple gradient background)
- Clean, modern design with clear visual hierarchy
- Use icons/symbols for different threat elements
- Professional fonts, high contrast for readability
- Aspect ratio: 16:9 (landscape)

CONTENT TO VISUALIZE:

TITLE: {article.title[:80]}

THREAT CATEGORIES: {categories}

VULNERABILITIES:
{vulnerabilities}

THREAT ACTORS:
{threat_actors}

SEVERITY LEVEL: {severity}

KEY FINDINGS:
{summary_text}

LAYOUT:
- Header with title and severity badge (color-coded: red=critical, orange=high, yellow=medium)
- Left section: Vulnerabilities with CVE badges
- Right section: Threat actors with icons
- Bottom: Key findings summary
- Include security-themed decorative elements (shields, locks, network nodes)

Make it look like a professional security operations center (SOC) dashboard or threat intelligence report."""

    def _build_timeline_prompt(
        self,
        article: Article,
        predictions: Optional[list[ThreatPrediction]] = None,
        timeline_events: Optional[list[dict]] = None,
    ) -> str:
        """Build prompt for timeline infographic."""
        events_text = ""
        if timeline_events:
            for i, event in enumerate(timeline_events[:6], 1):
                events_text += f"\n{i}. {event.get('title', 'Event')} - {event.get('timestamp', 'Unknown date')}"
        else:
            pub_date = article.published_at.strftime("%Y-%m-%d") if article.published_at else "Unknown"
            events_text = f"\n1. Initial Report - {pub_date}"

        prediction_text = ""
        if predictions and len(predictions) > 0:
            pred = predictions[0]
            confidence_pct = int(pred.confidence * 100) if pred.confidence else 0
            reasoning = pred.reasoning[:150] if pred.reasoning else "Based on threat intelligence analysis"
            prediction_text = f"""
PREDICTION:
- {confidence_pct}% probability
- {pred.description}
- Timeframe: Within {pred.timeframe_days} days
- Reasoning: {reasoning}"""

        return f"""Create a professional cybersecurity threat timeline infographic with the following design:

STYLE REQUIREMENTS:
- Dark theme with cyber/tech aesthetic
- Horizontal timeline layout
- Color-coded event markers (red for attacks, blue for disclosures, green for patches)
- Aspect ratio: 16:9 (landscape)

CONTENT TO VISUALIZE:

STORY TITLE: {article.title[:60]}

TIMELINE EVENTS:{events_text}
{prediction_text}

LAYOUT:
- Horizontal timeline with connected nodes
- Each event as a card/node with date and brief description
- If prediction exists, show it as a dashed/future node on the right
- Include threat severity indicators
- Add security-themed decorative elements

Make it look like a professional threat intelligence timeline from a SOC dashboard."""

    def _build_knowledge_graph_prompt(
        self,
        article: Article,
        graph: Optional[GraphVisualization] = None,
    ) -> str:
        """Build prompt for knowledge graph infographic."""
        nodes_text = ""
        if graph and graph.nodes:
            for node in graph.nodes[:10]:
                if isinstance(node, dict):
                    label = node.get("label", str(node))
                    node_type = node.get("node_type", "entity")
                elif hasattr(node, "label"):
                    label = node.label
                    node_type = getattr(node, "node_type", "entity")
                else:
                    label = str(node)
                    node_type = "entity"
                nodes_text += f"\n- {label} ({node_type})"
        else:
            # Fallback to article entities
            entities = article.vulnerabilities + article.threat_actors + article.categories
            for entity in entities[:10]:
                nodes_text += f"\n- {entity}"

        edges_text = ""
        if graph and graph.edges:
            for edge in graph.edges[:8]:
                if isinstance(edge, dict):
                    source = edge.get("source", "Unknown")
                    target = edge.get("target", "Unknown")
                    relationship = edge.get("relationship", "related_to")
                elif hasattr(edge, "source"):
                    source = edge.source
                    target = edge.target
                    relationship = getattr(edge, "relationship", "related_to")
                else:
                    continue
                edges_text += f"\n- {source} --[{relationship}]--> {target}"

        return f"""Create a professional cybersecurity knowledge graph infographic with the following design:

STYLE REQUIREMENTS:
- Dark theme with cyber/tech aesthetic (dark background, neon-style connections)
- Network graph visualization style
- Color-coded nodes by type (red=vulnerability, purple=threat_actor, blue=category, green=entity)
- Glowing connection lines
- Aspect ratio: 1:1 (square)

CONTENT TO VISUALIZE:

CENTRAL TOPIC: {article.title[:50]}

CONNECTED ENTITIES:{nodes_text if nodes_text else "\n- No entities extracted"}

RELATIONSHIPS:{edges_text if edges_text else "\n- Entities connected through article context"}

LAYOUT:
- Central node for the main article/topic
- Surrounding nodes for related entities
- Connecting lines showing relationships
- Node size based on importance
- Include a small legend for node colors
- Add subtle grid/matrix background effect

Make it look like a professional threat intelligence network visualization."""

    async def _generate_image(self, prompt: str) -> bytes:
        """Generate an image using Gemini API."""
        client = self._get_client()

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            # Extract image bytes from response
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    return part.inline_data.data

            raise ValueError("No image data in Gemini response")

        except Exception as e:
            logger.warning(
                "Primary model %s failed, trying fallback %s: %s",
                self.model,
                self.fallback_model,
                e,
            )
            # Try fallback model
            try:
                response = client.models.generate_content(
                    model=self.fallback_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                    ),
                )

                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        return part.inline_data.data

                raise ValueError("No image data from fallback model either")
            except Exception as fallback_error:
                logger.error("Fallback model also failed: %s", fallback_error)
                raise

    async def _upload_to_storage(
        self,
        image_bytes: bytes,
        path: str,
    ) -> str:
        """Upload image to Supabase Storage and return public URL."""
        supabase = get_supabase_client()

        try:
            # Delete existing file if it exists (for regeneration)
            try:
                supabase.storage.from_(self.bucket_name).remove([path])
            except Exception:
                pass  # File might not exist

            # Upload the new file
            supabase.storage.from_(self.bucket_name).upload(
                path=path,
                file=image_bytes,
                file_options={
                    "content-type": "image/png",
                },
            )

            # Get public URL
            public_url = supabase.storage.from_(self.bucket_name).get_public_url(path)

            return public_url

        except Exception as e:
            logger.error("Failed to upload to storage: %s", e)
            raise

    async def get_existing_infographic(
        self,
        article_id: str,
        infographic_type: InfographicType,
    ) -> Optional[str]:
        """Check if an infographic already exists and return its URL."""
        supabase = get_supabase_client()
        path = f"{article_id}/{infographic_type.value}.png"

        try:
            # List files in the article directory
            files = supabase.storage.from_(self.bucket_name).list(article_id)

            for file in files:
                if file.get("name") == f"{infographic_type.value}.png":
                    public_url = supabase.storage.from_(self.bucket_name).get_public_url(path)
                    return public_url

            return None

        except Exception as e:
            logger.debug("No existing infographic found: %s", e)
            return None


# Singleton instance
infographic_service = InfographicService()
