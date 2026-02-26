"""Binance Paper Trading Exchange Gateway

Uses real Binance market data but simulates order execution locally.
Orders are not sent to the exchange - execution is based on real prices.
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
from decimal import Decimal

from .base import ExchangeGateway
from ..order import Order
from ...core.types import OrderStatus, OrderSide, OrderType
from ...utils.logger import logger


class BinancePaperExchange(ExchangeGateway):
    """Binance Paper Trading Gateway

    Simulates all trading operations locally using real market prices from data feed.
    Perfect for testing strategies with real market conditions without risking capital.
    """

    def __init__(self, exchange_id: str, config: Dict):
        """Initialize Binance paper trading gateway

        Args:
            exchange_id: Exchange identifier
            config: Configuration including:
                - initial_balance: Starting virtual balance (default: 100000)
                - commission: Trading commission rate (default: 0.001)
                - slippage: Simulated slippage rate (default: 0.0005)
        """
        super().__init__(exchange_id, config)

        # Virtual account balances
        self.balances: Dict[str, Decimal] = {
            'USD': Decimal(str(config.get('initial_balance', '100000'))),
            'USDT': Decimal(str(config.get('initial_balance', '100000')))
        }

        # Virtual positions
        self.positions: Dict[str, Decimal] = {}

        # Order tracking
        self.orders: Dict[str, Order] = {}
        self.order_counter = 0

        # Trading parameters
        self.commission = Decimal(str(config.get('commission', '0.001')))
        self.slippage = Decimal(str(config.get('slippage', '0.0005')))

        # Price cache from market data feed
        self.price_cache: Dict[str, Decimal] = {}

        logger.info(f"Binance paper trading gateway initialized with ${self.balances['USD']} virtual capital")

    async def connect(self):
        """Connect to exchange (no-op for paper trading)"""
        self.is_connected = True
        logger.info("Binance paper trading gateway ready (using WebSocket data feed for prices)")

    async def disconnect(self):
        """Disconnect from exchange"""
        self.is_connected = False
        logger.info("Binance paper trading gateway disconnected")

    def update_price(self, symbol: str, price: Decimal):
        """Update cached price from market data feed

        Args:
            symbol: Trading symbol
            price: Latest price
        """
        self.price_cache[symbol] = price

    async def submit_order(self, order: Order) -> Order:
        """Submit order (simulated execution)

        Args:
            order: Order to submit

        Returns:
            Updated order with execution details
        """
        # Validate order
        is_valid, error_msg = self.validate_order(order)
        if not is_valid:
            order.status = OrderStatus.REJECTED
            order.status_message = error_msg
            logger.warning(f"Order rejected: {error_msg}")
            return order

        # Generate order ID
        self.order_counter += 1
        order.order_id = f"PAPER_{self.order_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        order.exchange_order_id = order.order_id

        # Get current market price
        try:
            current_price = await self.get_latest_price(order.symbol)
            if current_price is None:
                order.status = OrderStatus.REJECTED
                order.status_message = "Failed to get market price"
                return order

            # Calculate execution price with slippage
            if order.side == OrderSide.BUY:
                execution_price = current_price * (Decimal('1') + self.slippage)
            else:
                execution_price = current_price * (Decimal('1') - self.slippage)

            # For limit orders, use limit price if better
            if order.order_type == OrderType.LIMIT and order.price:
                if order.side == OrderSide.BUY and order.price < execution_price:
                    execution_price = order.price
                elif order.side == OrderSide.SELL and order.price > execution_price:
                    execution_price = order.price

            # Calculate costs
            order_value = execution_price * order.quantity
            commission = order_value * self.commission

            # Check if we have sufficient balance
            if order.side == OrderSide.BUY:
                total_cost = order_value + commission
                currency = self._get_quote_currency(order.symbol)

                if self.balances.get(currency, Decimal('0')) < total_cost:
                    order.status = OrderStatus.REJECTED
                    order.status_message = f"Insufficient balance: need {total_cost}, have {self.balances.get(currency, 0)}"
                    logger.warning(order.status_message)
                    return order

                # Execute buy
                self.balances[currency] -= total_cost
                base_currency = self._get_base_currency(order.symbol)
                self.positions[base_currency] = self.positions.get(base_currency, Decimal('0')) + order.quantity

            else:  # SELL
                base_currency = self._get_base_currency(order.symbol)

                if self.positions.get(base_currency, Decimal('0')) < order.quantity:
                    order.status = OrderStatus.REJECTED
                    order.status_message = f"Insufficient position: need {order.quantity}, have {self.positions.get(base_currency, 0)}"
                    logger.warning(order.status_message)
                    return order

                # Execute sell
                self.positions[base_currency] -= order.quantity
                currency = self._get_quote_currency(order.symbol)
                self.balances[currency] = self.balances.get(currency, Decimal('0')) + order_value - commission

            # Update order status
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_price = execution_price
            order.commission = commission
            order.filled_at = datetime.now()

            # Store order
            self.orders[order.order_id] = order

            logger.info(f"Order executed: {order.side.value} {order.quantity} {order.symbol} @ {execution_price} (commission: {commission})")

        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.status_message = f"Execution error: {str(e)}"
            logger.error(f"Failed to execute order: {e}")

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order (simulated)

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                order.status = OrderStatus.CANCELLED
                logger.info(f"Order cancelled: {order_id}")
                return True

        logger.warning(f"Cannot cancel order: {order_id}")
        return False

    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get order status

        Args:
            order_id: Order ID

        Returns:
            Order object if found
        """
        return self.orders.get(order_id)

    async def get_balance(self, currency: str = "USD") -> Decimal:
        """Get virtual account balance

        Args:
            currency: Currency code (USD, USDT, BTC, etc.)

        Returns:
            Balance amount
        """
        # Convert USD to USDT for Binance
        if currency == "USD":
            currency = "USDT"

        return self.balances.get(currency, Decimal('0'))

    async def get_position(self, symbol: str) -> Decimal:
        """Get virtual position

        Args:
            symbol: Trading symbol

        Returns:
            Position quantity
        """
        base_currency = self._get_base_currency(symbol)
        return self.positions.get(base_currency, Decimal('0'))

    async def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get latest price from cache

        Args:
            symbol: Trading symbol (e.g., 'BTC-USD')

        Returns:
            Latest price from cache
        """
        price = self.price_cache.get(symbol)
        if price is None:
            logger.warning(f"No price data available for {symbol}")
        return price

    def _get_base_currency(self, symbol: str) -> str:
        """Extract base currency from symbol

        Args:
            symbol: Trading symbol like 'BTC-USD'

        Returns:
            Base currency like 'BTC'
        """
        return symbol.split('-')[0].split('/')[0]

    def _get_quote_currency(self, symbol: str) -> str:
        """Extract quote currency from symbol

        Args:
            symbol: Trading symbol like 'BTC-USD'

        Returns:
            Quote currency like 'USDT' (converted from USD)
        """
        quote = symbol.split('-')[-1].split('/')[-1]
        # Convert USD to USDT for internal tracking
        if quote == 'USD':
            quote = 'USDT'
        return quote

    def get_account_summary(self) -> Dict:
        """Get account summary

        Returns:
            Dictionary with balances and positions
        """
        return {
            'balances': {k: float(v) for k, v in self.balances.items()},
            'positions': {k: float(v) for k, v in self.positions.items()},
            'total_orders': len(self.orders)
        }
