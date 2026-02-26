"""Console alert provider"""

from typing import Dict
from datetime import datetime

from .base import AlertProvider
from ...utils.logger import logger


class ConsoleAlertProvider(AlertProvider):
    """Console alert provider

    Output alerts to console/log
    """

    def __init__(self, provider_id: str = "console", config: Dict = None):
        super().__init__(provider_id, config)
        logger.info("Console alert provider initialized")

    async def send_alert(
        self,
        title: str,
        message: str,
        level: str = "INFO",
        metadata: Dict = None
    ) -> bool:
        """Send alert to console"""
        if not self.enabled:
            return False

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Select log method based on level
        log_message = f"[{level}] {title}: {message}"

        if level == "CRITICAL" or level == "ERROR":
            logger.error(log_message)
        elif level == "WARNING":
            logger.warning(log_message)
        else:
            logger.info(log_message)

        if metadata:
            logger.debug(f"Alert metadata: {metadata}")

        return True
