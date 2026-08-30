import pytest

from agents.execution_agent import ExecutionAgent, Order, OrderStatus, OrderType, TradingMode
from core.event_bus import EventType


@pytest.mark.asyncio
async def test_live_mode_without_broker_rejects_order_without_price_fallback():
    agent = ExecutionAgent(mode=TradingMode.LIVE)
    order = Order(
        order_id="order-1",
        symbol="BTC-USD",
        direction="BUY",
        order_type=OrderType.MARKET,
        quantity=1.0,
        limit_price=None,
        stop_price=None,
        stop_loss=90_000,
        take_profit=100_000,
    )
    agent._active_orders[order.symbol] = order.order_id
    published = []

    async def capture(event_type, payload, priority=5, correlation_id=None):
        published.append((event_type, payload, priority, correlation_id))

    agent.publish = capture

    await agent._live_execute(order)

    assert order.status == OrderStatus.REJECTED
    assert order.symbol not in agent._active_orders
    assert published == [
        (
            EventType.ORDER_REJECTED,
            {
                "order_id": "order-1",
                "symbol": "BTC-USD",
                "reason": "Live mode requires broker client",
            },
            3,
            None,
        )
    ]
