"""Telegram alert provider"""

from typing import Dict
import aiohttp

from .base import AlertProvider
from ...utils.logger import logger


class TelegramAlertProvider(AlertProvider):
    """Telegram alert provider"""

    def __init__(self, provider_id: str = "telegram", config: Dict = None):
        super().__init__(provider_id, config)

        # Telegram configuration
        self.bot_token = self.config.get('bot_token')
        self.chat_id = self.config.get('chat_id')

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram alert provider: missing credentials, will be disabled")
            self.enabled = False
        else:
            logger.info(f"Telegram alert provider initialized: chat_id={self.chat_id}")

    async def send_alert(
        self,
        title: str,
        message: str,
        level: str = "INFO",
        metadata: Dict = None
    ) -> bool:
        """Send Telegram alert"""
        if not self.enabled:
            return False

        try:
            # Build message
            emoji_map = {
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }
            emoji = emoji_map.get(level, 'ℹ️')

            text = f"{emoji} *{level}*: {title}\n\n{message}"

            if metadata:
                text += f"\n\n_Metadata: {metadata}_"

            # Send message
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Telegram alert sent: {title}")
                        return True
                    else:
                        logger.error(f"Telegram API error: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
