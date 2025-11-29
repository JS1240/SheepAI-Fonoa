"""Email service using Resend API for digest notifications."""

import logging
from datetime import datetime
from typing import Optional

import httpx

from app.config import settings
from app.models.notification import DigestFrequency

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications via Resend API."""

    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(self) -> None:
        self._api_key = settings.resend_api_key
        self._from_email = settings.email_from_address or "notifications@securityintel.dev"
        self._http_client: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self._api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def _format_digest_html(
        self,
        articles: list[dict],
        digest_type: DigestFrequency,
    ) -> str:
        """Format digest email as HTML."""
        frequency_label = {
            DigestFrequency.HOURLY: "Hourly",
            DigestFrequency.DAILY: "Daily",
            DigestFrequency.WEEKLY: "Weekly",
        }.get(digest_type, "")

        article_html = ""
        for article in articles:
            similarity_pct = int(article.get("similarity_score", 0) * 100)
            interest_text = article.get("interest_text", "your interests")

            article_html += f"""
            <div style="margin-bottom: 24px; padding: 16px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #0066cc;">
                <h3 style="margin: 0 0 8px 0; color: #1a1a1a;">
                    <a href="{article.get('url', '#')}" style="color: #0066cc; text-decoration: none;">
                        {article.get('title', 'Untitled Article')}
                    </a>
                </h3>
                <p style="margin: 0 0 8px 0; color: #666; font-size: 14px;">
                    {article.get('summary', '')[:200]}...
                </p>
                <p style="margin: 0; color: #888; font-size: 12px;">
                    Matched "{interest_text}" with {similarity_pct}% relevance
                </p>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="color: #1a1a1a; margin: 0;">Security Intelligence</h1>
                <p style="color: #666; margin: 8px 0 0 0;">{frequency_label} Digest - {datetime.utcnow().strftime('%B %d, %Y')}</p>
            </div>

            <p style="color: #333; margin-bottom: 24px;">
                We found <strong>{len(articles)}</strong> new article{"s" if len(articles) != 1 else ""} matching your interests:
            </p>

            {article_html}

            <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;">

            <p style="color: #888; font-size: 12px; text-align: center;">
                You're receiving this email because you subscribed to security intelligence notifications.
                <br>
                <a href="#" style="color: #0066cc;">Manage preferences</a> | <a href="#" style="color: #0066cc;">Unsubscribe</a>
            </p>
        </body>
        </html>
        """

    def _format_digest_text(
        self,
        articles: list[dict],
        digest_type: DigestFrequency,
    ) -> str:
        """Format digest email as plain text."""
        frequency_label = {
            DigestFrequency.HOURLY: "Hourly",
            DigestFrequency.DAILY: "Daily",
            DigestFrequency.WEEKLY: "Weekly",
        }.get(digest_type, "")

        lines = [
            f"Security Intelligence {frequency_label} Digest",
            f"Date: {datetime.utcnow().strftime('%B %d, %Y')}",
            "",
            f"We found {len(articles)} new article{'s' if len(articles) != 1 else ''} matching your interests:",
            "",
        ]

        for i, article in enumerate(articles, 1):
            similarity_pct = int(article.get("similarity_score", 0) * 100)
            interest_text = article.get("interest_text", "your interests")

            lines.extend([
                f"{i}. {article.get('title', 'Untitled Article')}",
                f"   URL: {article.get('url', 'N/A')}",
                f"   Matched \"{interest_text}\" with {similarity_pct}% relevance",
                "",
            ])

        lines.extend([
            "---",
            "Manage your notification preferences in the Security Intelligence dashboard.",
        ])

        return "\n".join(lines)

    async def send_digest_email(
        self,
        to_email: str,
        articles: list[dict],
        digest_type: DigestFrequency,
    ) -> bool:
        """Send a digest email to a user.

        Args:
            to_email: Recipient email address.
            articles: List of article dicts with title, url, summary, similarity_score, interest_text.
            digest_type: The frequency of the digest.

        Returns:
            True if email was sent successfully.
        """
        if not self.is_configured():
            logger.warning("Email service not configured, skipping send")
            return False

        if not articles:
            logger.debug("No articles to send, skipping email")
            return False

        frequency_label = {
            DigestFrequency.HOURLY: "Hourly",
            DigestFrequency.DAILY: "Daily",
            DigestFrequency.WEEKLY: "Weekly",
        }.get(digest_type, "")

        subject = f"Security Intelligence {frequency_label} Digest - {len(articles)} New Article{'s' if len(articles) != 1 else ''}"

        try:
            client = await self._get_client()
            response = await client.post(
                self.RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": self._from_email,
                    "to": [to_email],
                    "subject": subject,
                    "html": self._format_digest_html(articles, digest_type),
                    "text": self._format_digest_text(articles, digest_type),
                },
            )

            if response.status_code in (200, 201):
                logger.info("Sent digest email to %s with %d articles", to_email, len(articles))
                return True

            logger.error(
                "Failed to send email to %s: %s - %s",
                to_email,
                response.status_code,
                response.text,
            )
            return False

        except Exception as e:
            logger.error("Error sending email to %s: %s", to_email, e)
            return False


email_service = EmailService()
