"""Alert system base class"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from datetime import datetime

from ...utils.logger import logger


class AlertProvider(ABC):
    """Alert provider base class"""

    def __init__(self, provider_id: str, config: Dict = None):
        """Initialize alert provider

        Args:
            provider_id: Provider ID
            config: Configuration information
        """
        self.provider_id = provider_id
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)

    @abstractmethod
    async def send_alert(
        self,
        title: str,
        message: str,
        level: str = "INFO",
        metadata: Dict = None
    ) -> bool:
        """Send alert

        Args:
            title: Alert title
            message: Alert message
            level: Alert level (INFO, WARNING, ERROR, CRITICAL)
            metadata: Additional metadata

        Returns:
            Whether sending was successful
        """
        pass

    def is_enabled(self) -> bool:
        """Check if enabled"""
        return self.enabled

    def enable(self):
        """Enable alert"""
        self.enabled = True
        logger.info(f"Alert provider {self.provider_id} enabled")

    def disable(self):
        """Disable alert"""
        self.enabled = False
        logger.info(f"Alert provider {self.provider_id} disabled")
