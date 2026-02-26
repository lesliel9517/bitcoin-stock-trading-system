"""Order manager for handling order lifecycle"""

import asyncio
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import logging

from .order import Order
from .exchanges.base import ExchangeGateway
from ..core.event import OrderEvent, FillEvent
from ..core.event_bus import EventBus
from ..core.types import OrderStatus, OrderSide
from ..utils.logger import logger


class OrderManager:
    """Order manager

    Manages complete order lifecycle: create, submit, update, cancel
    """

    def __init__(self, event_bus: EventBus, exchange: ExchangeGateway):
        """Initialize order manager

        Args:
            event_bus: Event bus
            exchange: Exchange gateway
        """
        self.event_bus = event_bus
        self.exchange = exchange
        self.orders: Dict[str, Order] = {}
        self.active_orders: Dict[str, Order] = {}

        logger.info("Order manager initialized")

    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: str = "MARKET",
        price: Optional[Decimal] = None,
        strategy_id: str = ""
    ) -> Order:
        """Create order

        Args:
            symbol: Trading pair symbol
            side: Buy/sell direction
            quantity: Quantity
            order_type: Order type
            price: Price (required for limit orders)
            strategy_id: Strategy ID

        Returns:
            Order object
        """
        from ..core.types import OrderType as OT

        # Create order object
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OT[order_type],
            price=price,
            exchange=self.exchange.exchange_id,
            strategy_id=strategy_id,
            created_at=datetime.now()
        )

        # Save order
        self.orders[order.order_id] = order
        self.active_orders[order.order_id] = order

        # Publish order event
        from ..core.event import EventType
        await self.event_bus.publish(OrderEvent(
            event_type=EventType.ORDER,
            order_id=order.order_id,
            symbol=symbol,
            order_type=order_type,
            side=side.value,
            quantity=quantity,
            price=price,
            status=OrderStatus.PENDING.value,
            exchange=self.exchange.exchange_id,
            strategy_id=strategy_id,
            timestamp=datetime.now(),
            data={},
            source="order_manager"
        ))

        logger.info(f"Order created: {order.order_id} - {side.value} {quantity} {symbol}")
        return order

    async def submit_order(self, order: Order) -> Order:
        """Submit order to exchange

        Args:
            order: Order object

        Returns:
            Updated order object
        """
        logger.info(f"Submitting order: {order.order_id}")

        # Update status to submitted
        order.status = OrderStatus.SUBMITTED
        order.updated_at = datetime.now()

        # Submit to exchange
        updated_order = await self.exchange.submit_order(order)

        # Update local order
        self.orders[order.order_id] = updated_order

        # If order is completed, remove from active orders
        if updated_order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            self.active_orders.pop(order.order_id, None)

        # Publish order update event
        from ..core.event import EventType
        await self.event_bus.publish(OrderEvent(
            event_type=EventType.ORDER,
            order_id=updated_order.order_id,
            symbol=updated_order.symbol,
            order_type=updated_order.order_type.value,
            side=updated_order.side.value,
            quantity=updated_order.quantity,
            price=updated_order.price,
            status=updated_order.status.value,
            exchange=updated_order.exchange,
            strategy_id=updated_order.strategy_id,
            timestamp=datetime.now(),
            data={},
            source="order_manager"
        ))

        # If order is filled, publish fill event
        if updated_order.status == OrderStatus.FILLED:
            await self.event_bus.publish(FillEvent(
                event_type=EventType.FILL,
                order_id=updated_order.order_id,
                symbol=updated_order.symbol,
                side=updated_order.side.value,
                quantity=updated_order.filled_quantity,
                price=updated_order.average_price,
                commission=updated_order.commission,
                exchange=updated_order.exchange,
                fill_id=f"fill_{updated_order.order_id}",
                timestamp=datetime.now(),
                data={},
                source="order_manager"
            ))

        logger.info(f"Order {order.order_id} status: {updated_order.status.value}")
        return updated_order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order

        Args:
            order_id: Order ID

        Returns:
            Whether successfully cancelled
        """
        if order_id not in self.orders:
            logger.warning(f"Order not found: {order_id}")
            return False

        order = self.orders[order_id]

        # Can only cancel active orders
        if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            logger.warning(f"Cannot cancel order in status: {order.status.value}")
            return False

        # Cancel order
        success = await self.exchange.cancel_order(order_id)

        if success:
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now()
            self.active_orders.pop(order_id, None)

            # Publish order cancel event
            from ..core.event import EventType
            await self.event_bus.publish(OrderEvent(
                event_type=EventType.ORDER,
                order_id=order.order_id,
                symbol=order.symbol,
                order_type=order.order_type.value,
                side=order.side.value,
                quantity=order.quantity,
                price=order.price,
                status=OrderStatus.CANCELLED.value,
                exchange=order.exchange,
                strategy_id=order.strategy_id,
                timestamp=datetime.now(),
                data={},
                source="order_manager"
            ))

            logger.info(f"Order cancelled: {order_id}")

        return success

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order

        Args:
            order_id: Order ID

        Returns:
            Order object
        """
        return self.orders.get(order_id)

    def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get active orders

        Args:
            symbol: Trading pair symbol (optional)

        Returns:
            Order list
        """
        orders = list(self.active_orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    def get_all_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all orders

        Args:
            symbol: Trading pair symbol (optional)

        Returns:
            Order list
        """
        orders = list(self.orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    async def cancel_all_orders(self, symbol: Optional[str] = None):
        """Cancel all active orders

        Args:
            symbol: Trading pair symbol (optional, if specified only cancel orders for this symbol)
        """
        active_orders = self.get_active_orders(symbol)
        logger.info(f"Cancelling {len(active_orders)} active orders")

        tasks = [self.cancel_order(order.order_id) for order in active_orders]
        await asyncio.gather(*tasks)
