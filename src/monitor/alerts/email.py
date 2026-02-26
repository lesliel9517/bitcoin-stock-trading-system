"""Email alert provider"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
from datetime import datetime

from .base import AlertProvider
from ...utils.logger import logger


class EmailAlertProvider(AlertProvider):
    """Email alert provider"""

    def __init__(self, provider_id: str = "email", config: Dict = None):
        super().__init__(provider_id, config)

        # SMTP configuration
        self.smtp_host = self.config.get('smtp_host', 'smtp.gmail.com')
        self.smtp_port = self.config.get('smtp_port', 587)
        self.from_email = self.config.get('from_email')
        self.password = self.config.get('password')
        self.to_emails = self.config.get('to_emails', [])

        if not self.from_email or not self.password:
            logger.warning("Email alert provider: missing credentials, will be disabled")
            self.enabled = False
        else:
            logger.info(f"Email alert provider initialized: {self.from_email} -> {self.to_emails}")

    async def send_alert(
        self,
        title: str,
        message: str,
        level: str = "INFO",
        metadata: Dict = None
    ) -> bool:
        """Send email alert"""
        if not self.enabled:
            return False

        if not self.to_emails:
            logger.warning("No recipient emails configured")
            return False

        try:
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{level}] Trading Alert: {title}"

            # Email body
            body = f"""
Trading System Alert

Level: {level}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Title: {title}

Message:
{message}
"""

            if metadata:
                body += f"\n\nMetadata:\n{metadata}"

            msg.attach(MIMEText(body, 'plain'))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.password)
                server.send_message(msg)

            logger.info(f"Email alert sent: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
