"""Monitoring engine"""

import asyncio
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from .metrics import MetricsCollector
from .alerts.base import AlertProvider
from .alerts.console import ConsoleAlertProvider
from ..trading.portfolio import Portfolio
from ..core.event_bus import EventBus
from ..core.event import EventType, RiskEvent, FillEvent
from ..utils.logger import logger


class MonitoringEngine:
    """Monitoring engine

    Integrates metrics collection and alert system
    """

    def __init__(self, event_bus: EventBus, portfolio: Portfolio, config: Dict = None):
        """Initialize monitoring engine

        Args:
            event_bus: Event bus
            portfolio: Portfolio
            config: Configuration information
        """
        self.event_bus = event_bus
        self.portfolio = portfolio
        self.config = config or {}

        # Metrics collector
        self.metrics_collector = MetricsCollector(
            window_size=self.config.get('metrics_window', 100)
        )

        # Alert provider list
        self.alert_providers: List[AlertProvider] = []

        # Monitoring parameters
        self.update_interval = self.config.get('update_interval', 60)  # seconds
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Initialize alert providers
        self._init_alert_providers()

        # Subscribe to events
        self.event_bus.subscribe(EventType.RISK, self.on_risk_event)
        self.event_bus.subscribe(EventType.FILL, self.on_fill_event)

        logger.info("Monitoring engine initialized")

    def _init_alert_providers(self):
        """Initialize alert providers"""
        # Console alert (enabled by default)
        console_provider = ConsoleAlertProvider(config={'enabled': True})
        self.add_alert_provider(console_provider)

        # Email alert
        email_config = self.config.get('email')
        if email_config and email_config.get('enabled'):
            from .alerts.email import EmailAlertProvider
            email_provider = EmailAlertProvider(config=email_config)
            self.add_alert_provider(email_provider)

        # Telegram alert
        telegram_config = self.config.get('telegram')
        if telegram_config and telegram_config.get('enabled'):
            from .alerts.telegram import TelegramAlertProvider
            telegram_provider = TelegramAlertProvider(config=telegram_config)
            self.add_alert_provider(telegram_provider)

    def add_alert_provider(self, provider: AlertProvider):
        """Add alert provider

        Args:
            provider: Alert provider
        """
        self.alert_providers.append(provider)
        logger.info(f"Alert provider added: {provider.provider_id}")

    async def send_alert(
        self,
        title: str,
        message: str,
        level: str = "INFO",
        metadata: Dict = None
    ):
        """Send alert to all providers

        Args:
            title: Alert title
            message: Alert message
            level: Alert level
            metadata: Additional metadata
        """
        tasks = []
        for provider in self.alert_providers:
            if provider.is_enabled():
                task = provider.send_alert(title, message, level, metadata)
                tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def on_risk_event(self, event: RiskEvent):
        """Handle risk event

        Args:
            event: Risk event
        """
        # Send alert
        await self.send_alert(
            title=f"Risk Alert: {event.risk_type}",
            message=event.message,
            level=event.severity,
            metadata={
                'action': event.action,
                'symbol': event.affected_symbol,
                'timestamp': event.timestamp.isoformat()
            }
        )

    async def on_fill_event(self, event: FillEvent):
        """Handle fill event

        Args:
            event: Fill event
        """
        # Record trade
        trade = {
            'timestamp': event.timestamp,
            'symbol': event.symbol,
            'side': event.side,
            'quantity': float(event.quantity),
            'price': float(event.price),
            'commission': float(event.commission),
            'pnl': 0.0  # Needs to be calculated later
        }
        self.metrics_collector.record_trade(trade)

    async def start(self):
        """Start monitoring"""
        if self.is_running:
            logger.warning("Monitoring engine is already running")
            return

        self.is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Monitoring engine started")

    async def stop(self):
        """Stop monitoring"""
        if not self.is_running:
            return

        self.is_running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Monitoring engine stopped")

    async def _monitor_loop(self):
        """Monitoring loop"""
        while self.is_running:
            try:
                # Record current equity
                current_equity = self.portfolio.get_total_value()
                self.metrics_collector.record_equity(current_equity)

                # Check alert conditions
                await self._check_alert_conditions()

                # Wait for next update
                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.update_interval)

    async def _check_alert_conditions(self):
        """Check alert conditions"""
        metrics = self.metrics_collector.get_current_metrics(self.portfolio)

        # Check maximum drawdown
        max_drawdown_threshold = self.config.get('alert_max_drawdown', 15.0)
        if metrics['max_drawdown'] > max_drawdown_threshold:
            await self.send_alert(
                title="High Drawdown Alert",
                message=f"Current drawdown {metrics['max_drawdown']:.2f}% exceeds threshold {max_drawdown_threshold}%",
                level="WARNING",
                metadata={'drawdown': metrics['max_drawdown']}
            )

        # Check win rate
        if metrics['total_trades'] >= 10:  # At least 10 trades
            min_win_rate = self.config.get('alert_min_win_rate', 30.0)
            if metrics['win_rate'] < min_win_rate:
                await self.send_alert(
                    title="Low Win Rate Alert",
                    message=f"Win rate {metrics['win_rate']:.2f}% below threshold {min_win_rate}%",
                    level="WARNING",
                    metadata={'win_rate': metrics['win_rate'], 'trades': metrics['total_trades']}
                )

    def get_current_metrics(self) -> Dict:
        """Get current metrics

        Returns:
            Metrics dictionary
        """
        return self.metrics_collector.get_current_metrics(self.portfolio)

    def get_recent_performance(self, minutes: int = 60) -> Dict:
        """Get recent performance

        Args:
            minutes: Time window (minutes)

        Returns:
            Performance metrics
        """
        return self.metrics_collector.get_recent_performance(minutes)

    def get_dashboard_data(self) -> Dict:
        """Get monitoring dashboard data

        Returns:
            Dashboard data
        """
        metrics = self.get_current_metrics()
        recent_perf = self.get_recent_performance(60)

        return {
            'current_metrics': metrics,
            'recent_performance': recent_perf,
            'alert_providers': [
                {
                    'id': p.provider_id,
                    'enabled': p.is_enabled()
                }
                for p in self.alert_providers
            ]
        }
