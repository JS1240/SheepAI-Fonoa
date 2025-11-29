"""Infographic generation service using Google Gemini API with SVG fallback."""

import base64
import io
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

# Check if cairosvg is available for SVG to PNG conversion
# Note: cairosvg requires native Cairo library, which may not be installed
HAS_CAIROSVG = False
try:
    import cairosvg
    HAS_CAIROSVG = True
except (ImportError, OSError) as e:
    # OSError if cairo native lib not found, ImportError if package not installed
    logger.info("cairosvg not available (%s), SVG fallback will return SVG data directly", type(e).__name__)


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

            # Generate image with Gemini (or SVG fallback)
            image_bytes = await self._generate_image(prompt, infographic_type, article)

            # Determine file extension based on content
            is_svg = image_bytes.startswith(b'<?xml') or image_bytes.startswith(b'<svg')
            file_ext = "svg" if is_svg else "png"
            content_type = "image/svg+xml" if is_svg else "image/png"

            # Upload to Supabase Storage
            storage_path = f"{article.id}/{infographic_type.value}.{file_ext}"
            public_url = await self._upload_to_storage(
                image_bytes=image_bytes,
                path=storage_path,
                content_type=content_type,
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
                # Handle both dict and Pydantic model cases
                if isinstance(event, dict):
                    title = event.get('title', 'Event')
                    timestamp = event.get('timestamp', 'Unknown date')
                elif hasattr(event, 'title'):
                    title = event.title
                    timestamp = getattr(event, 'timestamp', getattr(event, 'date', 'Unknown date'))
                else:
                    title = str(event)
                    timestamp = 'Unknown date'
                events_text += f"\n{i}. {title} - {timestamp}"
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

    async def _generate_image(self, prompt: str, infographic_type: InfographicType = None, article: Article = None) -> bytes:
        """Generate an image using Gemini API with SVG fallback."""
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
            error_str = str(e)

            # Check if this is a billing/quota issue - use SVG fallback
            if any(msg in error_str for msg in ["RESOURCE_EXHAUSTED", "not available in your", "quota", "billing"]):
                logger.info("Gemini image generation not available (quota/billing), using SVG fallback")
                return await self._generate_svg_fallback(infographic_type, article)

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
                error_str = str(fallback_error)
                # Check again for billing issues on fallback
                if any(msg in error_str for msg in ["RESOURCE_EXHAUSTED", "not available in your", "quota", "billing", "not supported"]):
                    logger.info("Fallback model also not available, using SVG fallback")
                    return await self._generate_svg_fallback(infographic_type, article)
                logger.error("Fallback model also failed: %s", fallback_error)
                raise

    async def _generate_svg_fallback(self, infographic_type: InfographicType, article: Article) -> bytes:
        """Generate an SVG-based infographic as fallback when Gemini is not available."""
        if infographic_type == InfographicType.THREAT_SUMMARY:
            svg_content = self._create_threat_summary_svg(article)
        elif infographic_type == InfographicType.TIMELINE:
            svg_content = self._create_timeline_svg(article)
        elif infographic_type == InfographicType.KNOWLEDGE_GRAPH:
            svg_content = self._create_knowledge_graph_svg(article)
        else:
            svg_content = self._create_generic_svg(article)

        # Convert SVG to PNG if cairosvg is available
        if HAS_CAIROSVG:
            png_bytes = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'))
            return png_bytes
        else:
            # Return SVG as-is (frontend can display it)
            return svg_content.encode('utf-8')

    def _create_threat_summary_svg(self, article: Article) -> str:
        """Create a threat summary SVG infographic."""
        title = article.title[:60] + "..." if len(article.title) > 60 else article.title
        vulnerabilities = article.vulnerabilities[:4] if article.vulnerabilities else []
        threat_actors = article.threat_actors[:4] if article.threat_actors else []
        categories = article.categories[:3] if article.categories else ["Security"]

        # Determine severity
        content_lower = (article.content or "").lower()
        if any(t in content_lower for t in ["critical", "zero-day", "rce", "actively exploited"]):
            severity = "CRITICAL"
            severity_color = "#ef4444"
        elif any(t in content_lower for t in ["high", "important", "urgent"]):
            severity = "HIGH"
            severity_color = "#f97316"
        else:
            severity = "MEDIUM"
            severity_color = "#eab308"

        # Build vulnerability list
        vuln_items = ""
        for i, v in enumerate(vulnerabilities):
            vuln_items += f'''<text x="60" y="{295 + i*25}" fill="#f87171" font-size="14">{v[:30]}</text>'''
        if not vulnerabilities:
            vuln_items = '<text x="60" y="295" fill="#6b7280" font-size="14">None identified</text>'

        # Build threat actor list
        actor_items = ""
        for i, a in enumerate(threat_actors):
            actor_items += f'''<text x="450" y="{295 + i*25}" fill="#a78bfa" font-size="14">{a[:25]}</text>'''
        if not threat_actors:
            actor_items = '<text x="450" y="295" fill="#6b7280" font-size="14">None identified</text>'

        # Build category badges
        cat_badges = ""
        for i, c in enumerate(categories):
            cat_badges += f'''
            <rect x="{30 + i*120}" y="170" width="110" height="28" rx="14" fill="#3b82f6" opacity="0.3"/>
            <text x="{85 + i*120}" y="189" fill="#60a5fa" font-size="12" text-anchor="middle">{c[:15]}</text>'''

        summary = (article.summary or article.content or "")[:150]
        if len(summary) == 150:
            summary += "..."

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="800" height="500">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f172a"/>
      <stop offset="100%" style="stop-color:#1e1b4b"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="800" height="500" fill="url(#bgGrad)"/>

  <!-- Grid pattern -->
  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e3a5f" stroke-width="0.5" opacity="0.3"/>
  </pattern>
  <rect width="800" height="500" fill="url(#grid)"/>

  <!-- Header -->
  <rect x="20" y="20" width="760" height="80" rx="10" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="40" y="55" fill="#f8fafc" font-size="18" font-weight="bold" font-family="Arial, sans-serif">{title}</text>

  <!-- Severity Badge -->
  <rect x="650" y="35" width="110" height="35" rx="6" fill="{severity_color}" opacity="0.2" stroke="{severity_color}"/>
  <text x="705" y="58" fill="{severity_color}" font-size="14" font-weight="bold" text-anchor="middle" filter="url(#glow)">{severity}</text>

  <!-- Shield icon -->
  <circle cx="60" y="50" r="18" fill="#3b82f6" opacity="0.2"/>
  <text x="60" y="56" fill="#60a5fa" font-size="20" text-anchor="middle">&#x1F6E1;</text>

  <!-- Date -->
  <text x="40" y="78" fill="#94a3b8" font-size="12">Security Intelligence Report</text>

  <!-- Categories Section -->
  <text x="30" y="155" fill="#cbd5e1" font-size="14" font-weight="bold">CATEGORIES</text>
  {cat_badges}

  <!-- Vulnerabilities Section -->
  <rect x="30" y="220" width="350" height="140" rx="8" fill="#1e293b" stroke="#dc2626" stroke-width="1" opacity="0.5"/>
  <text x="50" y="250" fill="#fca5a5" font-size="14" font-weight="bold">VULNERABILITIES</text>
  <line x1="50" y1="265" x2="350" y2="265" stroke="#dc2626" stroke-width="1" opacity="0.3"/>
  {vuln_items}

  <!-- Threat Actors Section -->
  <rect x="420" y="220" width="350" height="140" rx="8" fill="#1e293b" stroke="#7c3aed" stroke-width="1" opacity="0.5"/>
  <text x="440" y="250" fill="#c4b5fd" font-size="14" font-weight="bold">THREAT ACTORS</text>
  <line x1="440" y1="265" x2="740" y2="265" stroke="#7c3aed" stroke-width="1" opacity="0.3"/>
  {actor_items}

  <!-- Summary Section -->
  <rect x="30" y="380" width="740" height="100" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="50" y="410" fill="#94a3b8" font-size="14" font-weight="bold">KEY FINDINGS</text>
  <text x="50" y="435" fill="#e2e8f0" font-size="12" font-family="Arial, sans-serif">
    <tspan x="50" dy="0">{summary[:75]}</tspan>
    <tspan x="50" dy="18">{summary[75:150] if len(summary) > 75 else ""}</tspan>
  </text>

  <!-- Footer branding -->
  <text x="400" y="490" fill="#475569" font-size="10" text-anchor="middle">Generated by Security Intelligence Platform</text>
</svg>'''

    def _create_timeline_svg(self, article: Article) -> str:
        """Create a timeline SVG infographic."""
        title = article.title[:50] + "..." if len(article.title) > 50 else article.title
        pub_date = article.published_at.strftime("%Y-%m-%d") if article.published_at else "Unknown"

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400" width="800" height="400">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f172a"/>
      <stop offset="100%" style="stop-color:#0c4a6e"/>
    </linearGradient>
  </defs>

  <rect width="800" height="400" fill="url(#bgGrad)"/>

  <!-- Title -->
  <text x="400" y="40" fill="#f8fafc" font-size="16" font-weight="bold" text-anchor="middle" font-family="Arial">{title}</text>

  <!-- Timeline line -->
  <line x1="80" y1="200" x2="720" y2="200" stroke="#3b82f6" stroke-width="3"/>

  <!-- Timeline nodes -->
  <circle cx="150" cy="200" r="15" fill="#3b82f6" stroke="#60a5fa" stroke-width="2"/>
  <text x="150" y="240" fill="#60a5fa" font-size="11" text-anchor="middle">Initial Report</text>
  <text x="150" y="255" fill="#94a3b8" font-size="10" text-anchor="middle">{pub_date}</text>

  <circle cx="320" cy="200" r="15" fill="#8b5cf6" stroke="#a78bfa" stroke-width="2"/>
  <text x="320" y="240" fill="#a78bfa" font-size="11" text-anchor="middle">Analysis</text>
  <text x="320" y="255" fill="#94a3b8" font-size="10" text-anchor="middle">Ongoing</text>

  <circle cx="490" cy="200" r="15" fill="#f59e0b" stroke="#fbbf24" stroke-width="2"/>
  <text x="490" y="240" fill="#fbbf24" font-size="11" text-anchor="middle">Monitoring</text>
  <text x="490" y="255" fill="#94a3b8" font-size="10" text-anchor="middle">Active</text>

  <!-- Prediction node (dashed) -->
  <circle cx="660" cy="200" r="15" fill="none" stroke="#ef4444" stroke-width="2" stroke-dasharray="5,3"/>
  <text x="660" y="240" fill="#f87171" font-size="11" text-anchor="middle">Predicted</text>
  <text x="660" y="255" fill="#94a3b8" font-size="10" text-anchor="middle">Future</text>

  <!-- Legend -->
  <rect x="50" y="300" width="700" height="80" rx="8" fill="#1e293b" stroke="#334155"/>
  <text x="70" y="330" fill="#cbd5e1" font-size="12" font-weight="bold">TIMELINE LEGEND</text>
  <circle cx="90" cy="355" r="8" fill="#3b82f6"/>
  <text x="105" y="360" fill="#94a3b8" font-size="11">Initial Event</text>
  <circle cx="230" cy="355" r="8" fill="#8b5cf6"/>
  <text x="245" y="360" fill="#94a3b8" font-size="11">Analysis Phase</text>
  <circle cx="380" cy="355" r="8" fill="#f59e0b"/>
  <text x="395" y="360" fill="#94a3b8" font-size="11">Active Monitoring</text>
  <circle cx="540" cy="355" r="8" fill="none" stroke="#ef4444" stroke-dasharray="3,2"/>
  <text x="555" y="360" fill="#94a3b8" font-size="11">Predicted Development</text>

  <text x="400" y="390" fill="#475569" font-size="10" text-anchor="middle">Generated by Security Intelligence Platform</text>
</svg>'''

    def _create_knowledge_graph_svg(self, article: Article) -> str:
        """Create a knowledge graph SVG infographic."""
        title = article.title[:40] + "..." if len(article.title) > 40 else article.title

        # Collect entities
        entities = []
        if article.vulnerabilities:
            for v in article.vulnerabilities[:3]:
                entities.append(("vuln", v[:15], "#ef4444"))
        if article.threat_actors:
            for a in article.threat_actors[:3]:
                entities.append(("actor", a[:15], "#8b5cf6"))
        if article.categories:
            for c in article.categories[:2]:
                entities.append(("cat", c[:15], "#3b82f6"))

        # Generate entity nodes
        entity_nodes = ""
        entity_lines = ""
        positions = [(150, 120), (650, 120), (100, 280), (700, 280), (200, 350), (600, 350), (400, 380)]

        for i, (etype, label, color) in enumerate(entities[:7]):
            if i < len(positions):
                x, y = positions[i]
                # Connection line to center
                entity_lines += f'<line x1="400" y1="200" x2="{x}" y2="{y}" stroke="{color}" stroke-width="2" opacity="0.5"/>'
                # Node
                entity_nodes += f'''
                <circle cx="{x}" cy="{y}" r="40" fill="{color}" opacity="0.2" stroke="{color}" stroke-width="2"/>
                <text x="{x}" y="{y+5}" fill="{color}" font-size="11" text-anchor="middle" font-family="Arial">{label}</text>'''

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="800" height="450">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f172a"/>
      <stop offset="100%" style="stop-color:#312e81"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <rect width="800" height="450" fill="url(#bgGrad)"/>

  <!-- Grid effect -->
  <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
    <circle cx="25" cy="25" r="1" fill="#4338ca" opacity="0.3"/>
  </pattern>
  <rect width="800" height="450" fill="url(#grid)"/>

  <!-- Title -->
  <text x="400" y="35" fill="#f8fafc" font-size="16" font-weight="bold" text-anchor="middle" font-family="Arial">Knowledge Graph: {title}</text>

  <!-- Connection lines -->
  {entity_lines}

  <!-- Central node -->
  <circle cx="400" cy="200" r="60" fill="#0ea5e9" opacity="0.3" stroke="#38bdf8" stroke-width="3" filter="url(#glow)"/>
  <text x="400" y="195" fill="#38bdf8" font-size="12" text-anchor="middle" font-weight="bold">ARTICLE</text>
  <text x="400" y="212" fill="#7dd3fc" font-size="10" text-anchor="middle">Central Topic</text>

  <!-- Entity nodes -->
  {entity_nodes}

  <!-- Legend -->
  <rect x="20" y="400" width="760" height="40" rx="5" fill="#1e293b" opacity="0.8"/>
  <circle cx="60" cy="420" r="8" fill="#ef4444" opacity="0.5" stroke="#ef4444"/>
  <text x="75" y="424" fill="#fca5a5" font-size="10">Vulnerability</text>
  <circle cx="190" cy="420" r="8" fill="#8b5cf6" opacity="0.5" stroke="#8b5cf6"/>
  <text x="205" y="424" fill="#c4b5fd" font-size="10">Threat Actor</text>
  <circle cx="320" cy="420" r="8" fill="#3b82f6" opacity="0.5" stroke="#3b82f6"/>
  <text x="335" y="424" fill="#93c5fd" font-size="10">Category</text>
  <circle cx="440" cy="420" r="8" fill="#0ea5e9" opacity="0.5" stroke="#38bdf8"/>
  <text x="455" y="424" fill="#7dd3fc" font-size="10">Central Article</text>

  <text x="700" y="424" fill="#475569" font-size="9">Security Intelligence Platform</text>
</svg>'''

    def _create_generic_svg(self, article: Article) -> str:
        """Create a generic SVG infographic."""
        return self._create_threat_summary_svg(article)

    async def _ensure_bucket_exists(self, supabase) -> None:
        """Ensure the storage bucket exists, create if it doesn't."""
        try:
            # Try to list buckets to check if ours exists
            buckets = supabase.storage.list_buckets()
            bucket_names = [b.name for b in buckets]

            if self.bucket_name not in bucket_names:
                logger.info("Creating storage bucket: %s", self.bucket_name)
                supabase.storage.create_bucket(
                    self.bucket_name,
                    options={
                        "public": True,
                        "allowed_mime_types": ["image/png", "image/svg+xml", "image/jpeg"],
                        "file_size_limit": 10485760,  # 10MB
                    },
                )
                logger.info("Storage bucket created: %s", self.bucket_name)
        except Exception as e:
            # Bucket might already exist or we lack permissions
            logger.debug("Bucket check/create result: %s", e)

    async def _upload_to_storage(
        self,
        image_bytes: bytes,
        path: str,
        content_type: str = "image/png",
    ) -> str:
        """Upload image to Supabase Storage and return public URL.

        Falls back to returning a base64 data URL if storage upload fails.
        """
        supabase = get_supabase_client()

        # Ensure bucket exists before uploading
        await self._ensure_bucket_exists(supabase)

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
                    "content-type": content_type,
                },
            )

            # Get public URL
            public_url = supabase.storage.from_(self.bucket_name).get_public_url(path)

            return public_url

        except Exception as e:
            logger.warning("Failed to upload to storage, using data URL fallback: %s", e)
            # Fallback to base64 data URL when storage is unavailable
            import base64
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            return f"data:{content_type};base64,{b64_data}"

    async def get_existing_infographic(
        self,
        article_id: str,
        infographic_type: InfographicType,
    ) -> Optional[str]:
        """Check if an infographic already exists and return its URL."""
        supabase = get_supabase_client()

        try:
            # List files in the article directory
            files = supabase.storage.from_(self.bucket_name).list(article_id)

            # Check for both .png and .svg files
            for ext in ["png", "svg"]:
                filename = f"{infographic_type.value}.{ext}"
                for file in files:
                    if file.get("name") == filename:
                        path = f"{article_id}/{filename}"
                        public_url = supabase.storage.from_(self.bucket_name).get_public_url(path)
                        return public_url

            return None

        except Exception as e:
            logger.debug("No existing infographic found: %s", e)
            return None


# Singleton instance
infographic_service = InfographicService()
