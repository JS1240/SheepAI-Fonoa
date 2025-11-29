"""Telegram bot service for notifications using HTTP API with long polling."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx

from app.config import settings
from app.models.notification import DigestFrequency

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Service for Telegram bot notifications using HTTP API."""

    BASE_URL = "https://api.telegram.org/bot{token}"

    def __init__(self) -> None:
        self._token = settings.telegram_bot_token
        self._http_client: Optional[httpx.AsyncClient] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_update_id = 0
        self._link_callback: Optional[callable] = None

    def is_configured(self) -> bool:
        """Check if Telegram bot is properly configured."""
        return bool(self._token)

    @property
    def api_url(self) -> str:
        """Get the Telegram API base URL."""
        return self.BASE_URL.format(token=self._token)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    async def close(self) -> None:
        """Stop polling and close HTTP client."""
        self._running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def set_link_callback(self, callback: callable) -> None:
        """Set callback for handling account linking.

        The callback should accept (token: str, chat_id: int, username: str) -> bool
        """
        self._link_callback = callback

    async def start_polling(self) -> None:
        """Start long polling for updates."""
        if not self.is_configured():
            logger.warning("Telegram bot not configured, polling disabled")
            return

        if self._running:
            logger.debug("Polling already running")
            return

        self._running = True
        self._polling_task = asyncio.create_task(self._poll_loop())
        logger.info("Telegram bot polling started")

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._process_updates()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in polling loop: %s", e)
                await asyncio.sleep(5)

    async def _process_updates(self) -> None:
        """Fetch and process updates from Telegram."""
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.api_url}/getUpdates",
                params={
                    "offset": self._last_update_id + 1,
                    "timeout": 30,
                    "allowed_updates": ["message"],
                },
            )

            if response.status_code != 200:
                logger.error("Failed to get updates: %s", response.text)
                await asyncio.sleep(5)
                return

            data = response.json()
            if not data.get("ok"):
                logger.error("Telegram API error: %s", data)
                await asyncio.sleep(5)
                return

            for update in data.get("result", []):
                self._last_update_id = max(self._last_update_id, update["update_id"])
                await self._handle_update(update)

        except httpx.TimeoutException:
            pass
        except Exception as e:
            logger.error("Error fetching updates: %s", e)
            await asyncio.sleep(5)

    async def _handle_update(self, update: dict) -> None:
        """Handle a single update from Telegram."""
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        username = message.get("from", {}).get("username")

        if not chat_id:
            return

        if text.startswith("/start"):
            await self._handle_start_command(chat_id, text, username)
        elif text == "/status":
            await self._handle_status_command(chat_id)
        elif text == "/help":
            await self._handle_help_command(chat_id)
        else:
            await self._send_message(
                chat_id,
                "I don't understand that command. Use /help to see available commands.",
            )

    async def _handle_start_command(
        self,
        chat_id: int,
        text: str,
        username: Optional[str],
    ) -> None:
        """Handle /start command with optional linking token."""
        parts = text.split(maxsplit=1)

        if len(parts) == 2:
            token = parts[1].strip()
            if self._link_callback:
                success = await self._link_callback(token, chat_id, username)
                if success:
                    await self._send_message(
                        chat_id,
                        "Your account has been linked successfully. "
                        "You will now receive security intelligence notifications here.",
                    )
                else:
                    await self._send_message(
                        chat_id,
                        "Failed to link your account. The link may have expired. "
                        "Please try generating a new link from the dashboard.",
                    )
            else:
                await self._send_message(
                    chat_id,
                    "Account linking is not available at this time.",
                )
        else:
            await self._send_message(
                chat_id,
                "Welcome to Security Intelligence Bot.\n\n"
                "To link your account, please use the link from your dashboard.\n\n"
                "Commands:\n"
                "/status - Check your notification status\n"
                "/help - Get help",
            )

    async def _handle_status_command(self, chat_id: int) -> None:
        """Handle /status command."""
        await self._send_message(
            chat_id,
            "Your Telegram notifications are active.\n\n"
            "You will receive security intelligence digests "
            "when articles match your interests.",
        )

    async def _handle_help_command(self, chat_id: int) -> None:
        """Handle /help command."""
        await self._send_message(
            chat_id,
            "Security Intelligence Bot Help\n\n"
            "This bot sends you notifications about security news "
            "that matches your interests.\n\n"
            "Commands:\n"
            "/start - Link your account (use link from dashboard)\n"
            "/status - Check notification status\n"
            "/help - Show this help message\n\n"
            "To manage your interests and notification settings, "
            "visit the Security Intelligence dashboard.",
        )

    async def _send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
        disable_preview: bool = False,
    ) -> bool:
        """Send a message to a chat."""
        if not self.is_configured():
            return False

        client = await self._get_client()

        try:
            params = {
                "chat_id": chat_id,
                "text": text,
            }
            if parse_mode:
                params["parse_mode"] = parse_mode
            if disable_preview:
                params["disable_web_page_preview"] = True

            response = await client.post(
                f"{self.api_url}/sendMessage",
                json=params,
            )

            if response.status_code == 200:
                return True

            logger.error("Failed to send message: %s", response.text)
            return False

        except Exception as e:
            logger.error("Error sending message to %s: %s", chat_id, e)
            return False

    def _format_digest_message(
        self,
        articles: list[dict],
        digest_type: DigestFrequency,
    ) -> str:
        """Format digest as Telegram message with HTML."""
        frequency_label = {
            DigestFrequency.HOURLY: "Hourly",
            DigestFrequency.DAILY: "Daily",
            DigestFrequency.WEEKLY: "Weekly",
        }.get(digest_type, "")

        lines = [
            f"<b>Security Intelligence {frequency_label} Digest</b>",
            f"<i>{datetime.utcnow().strftime('%B %d, %Y')}</i>",
            "",
            f"Found <b>{len(articles)}</b> article{'s' if len(articles) != 1 else ''} matching your interests:",
            "",
        ]

        for i, article in enumerate(articles[:10], 1):
            similarity_pct = int(article.get("similarity_score", 0) * 100)
            interest_text = article.get("interest_text", "your interests")
            title = article.get("title", "Untitled")[:60]
            if len(article.get("title", "")) > 60:
                title += "..."

            lines.append(
                f"{i}. <a href=\"{article.get('url', '#')}\">{title}</a>\n"
                f"   <i>Matched \"{interest_text}\" ({similarity_pct}%)</i>"
            )
            lines.append("")

        if len(articles) > 10:
            lines.append(f"<i>...and {len(articles) - 10} more articles</i>")

        return "\n".join(lines)

    async def send_digest(
        self,
        chat_id: int,
        articles: list[dict],
        digest_type: DigestFrequency,
    ) -> bool:
        """Send a digest notification to a user.

        Args:
            chat_id: Telegram chat ID.
            articles: List of article dicts with title, url, summary, similarity_score, interest_text.
            digest_type: The frequency of the digest.

        Returns:
            True if message was sent successfully.
        """
        if not articles:
            logger.debug("No articles to send, skipping Telegram message")
            return False

        message = self._format_digest_message(articles, digest_type)
        success = await self._send_message(
            chat_id,
            message,
            parse_mode="HTML",
            disable_preview=True,
        )

        if success:
            logger.info(
                "Sent Telegram digest to %s with %d articles",
                chat_id,
                len(articles),
            )

        return success


telegram_bot_service = TelegramBotService()
