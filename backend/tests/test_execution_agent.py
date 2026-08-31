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


@pytest.mark.asyncio
async def test_live_mode_publishes_broker_fill():
    class FakeBroker:
        def submit_market_order(self, order):
            return {
                "ok": True,
                "broker": "exness_mt5",
                "symbol": "XAUUSDm",
                "fill_price": 2301.55,
                "fill_quantity": 1.0,
                "volume_lots": 0.01,
                "position_size_usd": 2301.55,
                "broker_order_id": 11,
                "broker_deal_id": 22,
            }

    agent = ExecutionAgent(mode=TradingMode.LIVE)
    agent.set_live_broker(FakeBroker())
    order = Order(
        order_id="order-2",
        symbol="XAUUSDm",
        direction="BUY",
        order_type=OrderType.MARKET,
        quantity=0.001,
        limit_price=None,
        stop_price=None,
        stop_loss=2200.0,
        take_profit=2400.0,
    )
    published = []

    async def capture(event_type, payload, priority=5, correlation_id=None):
        published.append((event_type, payload, priority, correlation_id))

    agent.publish = capture

    await agent._live_execute(order)

    assert order.status == OrderStatus.FILLED
    assert order.fill_price == 2301.55
    assert published[0][0] == EventType.ORDER_FILLED
    assert published[0][1]["broker"] == "exness_mt5"
    assert published[0][1]["broker_symbol"] == "XAUUSDm"
    assert published[1][0] == EventType.POSITION_OPENED
