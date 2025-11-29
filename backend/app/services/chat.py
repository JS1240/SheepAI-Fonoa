"""Chat service for conversational AI interface."""

import logging
import time
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings
from app.models.article import ArticleSummary
from app.models.conversation import (
    ConversationRequest,
    ConversationResponse,
    IntentType,
    ParsedIntent,
    StoryTimeline,
    TimelineEvent,
    EventType,
    UserPreferences,
    AudienceType,
    ExplainToRequest,
    ExplainToResponse,
)
from app.services.ingestion import ingestion_service
from app.services.intelligence import intelligence_service
from app.services.graph import graph_service
from app.services.prediction import prediction_service

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling conversational queries."""

    def __init__(self) -> None:
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.llm_model = settings.openai_model

    async def parse_intent(self, message: str) -> ParsedIntent:
        """Parse user intent from a message."""
        message_lower = message.lower()

        # Simple rule-based intent detection for MVP
        if any(word in message_lower for word in ["latest", "recent", "new", "show me"]):
            intent_type = IntentType.SHOW_LATEST
        elif any(word in message_lower for word in ["connect", "related", "link"]):
            intent_type = IntentType.SHOW_CONNECTIONS
        elif any(word in message_lower for word in ["evolve", "timeline", "history"]):
            intent_type = IntentType.SHOW_EVOLUTION
        elif any(word in message_lower for word in ["predict", "forecast", "expect"]):
            intent_type = IntentType.SHOW_PREDICTIONS
        elif any(word in message_lower for word in ["search", "find", "look for"]):
            intent_type = IntentType.SEARCH
        elif any(word in message_lower for word in ["explain", "what is", "tell me about"]):
            intent_type = IntentType.EXPLAIN
        else:
            intent_type = IntentType.SEARCH

        # Extract topic
        topic = self._extract_topic(message)

        return ParsedIntent(
            intent_type=intent_type,
            topic=topic,
            confidence=0.8,
        )

    def _find_best_connected_article(self, articles: list):
        """Find the article with the most graph connections for better visualization.

        This ensures the chat response includes rich graph data by selecting
        an article that has entity connections rather than always using the first result.
        """
        if not articles:
            return None

        best_article = articles[0]
        best_connection_count = 0

        for article in articles:
            # Check if article exists in graph and count its connections
            # Use depth=2 to match API behavior and find richer connections
            subgraph = graph_service.get_subgraph(article.id, depth=2)
            connection_count = subgraph.total_edges

            if connection_count > best_connection_count:
                best_connection_count = connection_count
                best_article = article
                logger.debug(
                    "Found better connected article: %s with %d connections",
                    article.id, connection_count
                )

        if best_connection_count > 0:
            logger.info(
                "Selected article with %d connections: %s",
                best_connection_count, best_article.title[:50]
            )

        return best_article

    def _extract_topic(self, message: str) -> Optional[str]:
        """Extract the main topic from a message."""
        message_lower = message.lower()

        # Common security topics
        topics = [
            "ransomware",
            "vulnerability",
            "malware",
            "phishing",
            "breach",
            "zero-day",
            "apt",
            "ddos",
            "exploit",
            "backdoor",
            "trojan",
            "supply chain",
            "apache",
            "microsoft",
            "linux",
            "windows",
            "cloud",
        ]

        for topic in topics:
            if topic in message_lower:
                return topic

        return None

    async def process_query(
        self,
        request: ConversationRequest,
    ) -> ConversationResponse:
        """Process a user query and generate a response."""
        start_time = time.time()

        # Parse intent
        intent = await self.parse_intent(request.message)
        logger.info("Parsed intent: %s, topic: %s", intent.intent_type, intent.topic)

        # Get relevant articles
        articles = await ingestion_service.search_articles(
            query=intent.topic,
            days=30,
        )

        if not articles:
            return ConversationResponse(
                response_text=(
                    f"I couldn't find any recent articles about '{intent.topic or 'that topic'}'. "
                    "Try searching for common security topics like ransomware, vulnerabilities, or breaches."
                ),
                query_understood=True,
                suggested_followups=[
                    "Show me the latest ransomware news",
                    "What vulnerabilities were disclosed this week?",
                    "Any recent data breaches?",
                ],
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Find the article with the most graph connections for better visualization
        # Check all search results since well-connected articles may not be most recent
        primary_article = self._find_best_connected_article(articles)

        # Build response components
        article_summaries = [
            ArticleSummary(
                id=a.id,
                title=a.title,
                url=a.url,
                summary=a.summary,
                published_at=a.published_at,
                categories=a.categories,
            )
            for a in articles[:5]
        ]

        # Get timeline if requested
        timeline = None
        if request.include_timeline:
            timeline = await self._build_timeline(primary_article, articles)

        # Get graph if requested
        graph_data = None
        if request.include_graph:
            graph_data = graph_service.get_subgraph(primary_article.id, depth=2)

        # Get predictions if requested (with graph intelligence)
        predictions = []
        if request.include_predictions:
            predictions = await prediction_service.get_predictions_for_article(
                primary_article,
                graph_service=graph_service,
            )

        # Generate conversational response
        response_text = await self._generate_response(
            intent=intent,
            primary_article=primary_article,
            article_count=len(articles),
            predictions=predictions,
            preferences=request.user_preferences,
        )

        # Generate follow-up suggestions
        suggested_followups = self._generate_followups(intent, primary_article)

        processing_time = int((time.time() - start_time) * 1000)

        return ConversationResponse(
            response_text=response_text,
            articles=article_summaries,
            timeline=timeline,
            graph_data=graph_data,
            predictions=predictions,
            query_understood=True,
            suggested_followups=suggested_followups,
            processing_time_ms=processing_time,
        )

    async def _build_timeline(
        self,
        primary_article,
        related_articles: list,
    ) -> StoryTimeline:
        """Build a timeline for a story."""
        events = []

        for article in related_articles[:10]:
            event_type = EventType.UPDATE

            content_lower = article.content.lower()
            if "disclosed" in content_lower or "discovered" in content_lower:
                event_type = EventType.DISCLOSURE
            elif "patch" in content_lower or "fix" in content_lower:
                event_type = EventType.PATCH
            elif "exploit" in content_lower or "attack" in content_lower:
                event_type = EventType.EXPLOIT
            elif "breach" in content_lower:
                event_type = EventType.BREACH

            severity = "medium"
            if "critical" in content_lower:
                severity = "critical"
            elif "high" in content_lower:
                severity = "high"

            events.append(
                TimelineEvent(
                    event_id=f"evt-{article.id}",
                    article_id=article.id,
                    title=article.title[:100],
                    event_type=event_type,
                    timestamp=article.published_at,
                    severity=severity,
                )
            )

        # Sort by timestamp
        events.sort(key=lambda x: x.timestamp)

        # Get prediction for the story (with graph intelligence)
        prediction = None
        predictions = await prediction_service.get_predictions_for_article(
            primary_article,
            graph_service=graph_service,
        )
        if predictions:
            prediction = predictions[0]

        return StoryTimeline(
            story_id=f"story-{primary_article.id}",
            title=primary_article.title,
            events=events,
            current_status="active",
            prediction=prediction,
            first_seen=events[0].timestamp if events else None,
            last_updated=events[-1].timestamp if events else None,
        )

    def _build_system_prompt(self, preferences: Optional[UserPreferences] = None) -> str:
        """Build a personalized system prompt based on user preferences."""
        base_prompt = "You are a cybersecurity intelligence assistant."

        if not preferences:
            return (
                f"{base_prompt} Provide a brief, professional summary of the security situation. "
                "Be concise (2-3 sentences). Focus on what security professionals need to know."
            )

        # Build personalized context
        context_parts = []

        # Add role and industry context
        if preferences.role and preferences.industry:
            context_parts.append(
                f"You are speaking to a {preferences.role} in the {preferences.industry} industry"
            )
        elif preferences.role:
            context_parts.append(f"You are speaking to a {preferences.role}")
        elif preferences.industry:
            context_parts.append(f"You are speaking to someone in the {preferences.industry} industry")

        # Add seniority context
        if preferences.seniority:
            context_parts.append(f"at the {preferences.seniority} level")

        # Build style instructions based on summary_style
        style_instructions = {
            "non-technical": (
                "Use clear, jargon-free language. Focus on business impact and actionable takeaways. "
                "Avoid technical acronyms unless absolutely necessary, and explain them when used."
            ),
            "technical": (
                "Include technical details like CVEs, IOCs, attack vectors, and affected systems. "
                "Be precise with terminology. Security professionals will understand the implications."
            ),
            "executive": (
                "Focus on business risk, strategic implications, and recommended actions. "
                "Quantify impact where possible. Be concise and decision-oriented."
            ),
        }

        # Build detail level instructions
        detail_instructions = {
            "brief": "Keep your response to 1-2 sentences. Hit the key points only.",
            "detailed": "Provide a thorough 3-4 sentence analysis with context.",
            "comprehensive": "Give a complete analysis covering context, implications, and recommendations.",
        }

        # Compose the prompt
        prompt_parts = [base_prompt]

        if context_parts:
            prompt_parts.append(" ".join(context_parts) + ".")

        # Add interests context
        if preferences.interests:
            interests_str = ", ".join(preferences.interests)
            prompt_parts.append(f"They are particularly interested in: {interests_str}.")

        # Add style and detail instructions
        style = preferences.summary_style or "technical"
        detail = preferences.detail_level or "detailed"

        prompt_parts.append(style_instructions.get(style, style_instructions["technical"]))
        prompt_parts.append(detail_instructions.get(detail, detail_instructions["detailed"]))

        return " ".join(prompt_parts)

    async def _generate_response(
        self,
        intent: ParsedIntent,
        primary_article,
        article_count: int,
        predictions: list,
        preferences: Optional[UserPreferences] = None,
    ) -> str:
        """Generate a natural language response."""
        try:
            prediction_text = ""
            if predictions:
                pred = predictions[0]
                prediction_text = (
                    f"\n\nPrediction: {pred.confidence_percentage}% probability of "
                    f"{pred.description} within {pred.timeframe_days} days."
                )

            system_prompt = self._build_system_prompt(preferences)

            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": (
                            f"User asked about: {intent.topic or 'latest security news'}\n"
                            f"Primary article: {primary_article.title}\n"
                            f"Summary: {primary_article.summary or primary_article.content[:500]}\n"
                            f"Found {article_count} related articles.\n"
                            f"{prediction_text}"
                        ),
                    },
                ],
                max_tokens=300,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error("Failed to generate response: %s", e)
            # Fallback response
            base = f"Here's what I found about {intent.topic or 'security news'}. "
            base += f"The latest article is: {primary_article.title}. "
            if primary_article.summary:
                base += primary_article.summary
            if predictions:
                pred = predictions[0]
                base += f" {pred.to_display_string()}."
            return base

    def _generate_followups(
        self,
        intent: ParsedIntent,
        primary_article,
    ) -> list[str]:
        """Generate follow-up question suggestions."""
        followups = []

        if intent.intent_type != IntentType.SHOW_CONNECTIONS:
            followups.append(f"What's connected to this {intent.topic or 'story'}?")

        if intent.intent_type != IntentType.SHOW_EVOLUTION:
            followups.append("How has this situation evolved?")

        if intent.intent_type != IntentType.SHOW_PREDICTIONS:
            followups.append("What should I expect next?")

        if primary_article.vulnerabilities:
            followups.append(
                f"Tell me more about {primary_article.vulnerabilities[0]}"
            )

        return followups[:3]


    async def translate_for_audience(
        self,
        request: ExplainToRequest,
    ) -> ExplainToResponse:
        """Translate threat content for a specific audience."""
        audience_prompts = {
            AudienceType.CEO: {
                "role": "a CEO who needs to understand business impact and make quick decisions",
                "focus": "business risk, financial impact, strategic decisions, and resource allocation",
                "style": "Clear, concise, decision-oriented. Avoid technical jargon. Focus on what they need to decide and when.",
                "actions": "executive-level actions like approving budgets, authorizing responses, stakeholder communication",
            },
            AudienceType.BOARD: {
                "role": "board members who need to understand governance and risk implications",
                "focus": "corporate risk, regulatory compliance, fiduciary responsibility, and strategic oversight",
                "style": "Formal, governance-focused. Emphasize risk management, compliance obligations, and strategic implications.",
                "actions": "governance actions like risk committee review, policy updates, compliance verification",
            },
            AudienceType.DEVELOPERS: {
                "role": "software developers who need technical details to implement fixes",
                "focus": "technical specifics, affected systems, remediation steps, and code-level changes",
                "style": "Technical and precise. Include specific technologies, versions, CVEs, and implementation details.",
                "actions": "technical actions like patching, code review, configuration changes, testing procedures",
            },
        }

        audience_config = audience_prompts[request.audience]

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a cybersecurity communication expert translating technical threat information for {audience_config['role']}. "
                            f"Focus on: {audience_config['focus']}. "
                            f"Communication style: {audience_config['style']} "
                            "Respond in JSON format with the following structure: "
                            '{"translated_content": "...", "key_points": ["...", "..."], "recommended_actions": ["...", "..."], "risk_level": "critical|high|medium|low", "business_impact": "..."}'
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Translate this security threat for {request.audience.value.upper()}:\n\n"
                            f"{request.content}\n\n"
                            f"Provide actions appropriate for {audience_config['actions']}."
                        ),
                    },
                ],
                max_tokens=800,
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            import json
            result = json.loads(response.choices[0].message.content)

            return ExplainToResponse(
                original_content=request.content,
                audience=request.audience,
                translated_content=result.get("translated_content", "Translation unavailable."),
                key_points=result.get("key_points", []),
                recommended_actions=result.get("recommended_actions", []),
                risk_level=result.get("risk_level", "medium"),
                business_impact=result.get("business_impact"),
            )

        except Exception as e:
            logger.error("Failed to translate for audience %s: %s", request.audience, e)
            # Provide a fallback response
            return ExplainToResponse(
                original_content=request.content,
                audience=request.audience,
                translated_content=f"Security alert requiring attention. Original content: {request.content[:200]}...",
                key_points=["Security incident detected", "Review required", "Await technical assessment"],
                recommended_actions=["Consult with security team", "Await detailed briefing"],
                risk_level="medium",
                business_impact="Assessment in progress.",
            )


# Singleton instance
chat_service = ChatService()
