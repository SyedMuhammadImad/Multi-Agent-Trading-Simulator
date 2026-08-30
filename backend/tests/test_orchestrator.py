import pytest

from core.event_bus import Event, EventType
from core.orchestrator import MasterOrchestrator


def signal(source_agent, direction="BUY", price=95_000):
    event_type = (
        EventType.STRATEGY_SIGNAL
        if source_agent == "strategy_agent"
        else EventType.SENTIMENT_SIGNAL
    )
    return Event(
        event_type=event_type,
        source_agent=source_agent,
        payload={
            "symbol": "BTC-USD",
            "direction": direction,
            "confidence": 0.95,
            "reasoning": "test signal",
            "price": price,
        },
    )


@pytest.mark.asyncio
async def test_orchestrator_dispatches_order_with_flat_signal_price():
    orchestrator = MasterOrchestrator()
    orchestrator._cooldown_seconds = 0
    published = []

    async def capture(event_type, payload, priority=5, correlation_id=None):
        published.append((event_type, payload, priority, correlation_id))

    orchestrator.publish = capture

    await orchestrator.process_event(signal("strategy_agent"))
    await orchestrator.process_event(signal("sentiment_agent"))

    orders = [payload for event_type, payload, _, _ in published if event_type == EventType.ORDER_REQUESTED]
    assert len(orders) == 1
    assert orders[0]["symbol"] == "BTC-USD"
    assert orders[0]["action"] == "EXECUTE_BUY"
    assert orders[0]["price"] == 95_000


@pytest.mark.asyncio
async def test_orchestrator_blocks_new_signal_orders_after_kill_switch():
    orchestrator = MasterOrchestrator()
    orchestrator._cooldown_seconds = 0
    published = []

    async def capture(event_type, payload, priority=5, correlation_id=None):
        published.append((event_type, payload, priority, correlation_id))

    orchestrator.publish = capture

    await orchestrator.process_event(Event(
        event_type=EventType.KILL_SWITCH_ACTIVATED,
        source_agent="risk_agent",
        payload={"reason": "test breach"},
    ))
    assert published[-1][1]["action"] == "CLOSE_ALL_POSITIONS"

    published.clear()
    await orchestrator.process_event(signal("strategy_agent"))
    await orchestrator.process_event(signal("sentiment_agent"))

    assert published == []
