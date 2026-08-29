"""Unit tests for generic StateMachine implementation."""

import pytest
from enum import Enum, auto
from dataclasses import dataclass, field

from app.common.state_machine import StateMachine, InvalidTransition


class SampleState(Enum):
    """Sample states for FSM testing."""

    DRAFT = auto()
    ACTIVE = auto()
    CLOSED = auto()


class SampleEvent(Enum):
    """Sample events for FSM testing."""

    ACTIVATE = auto()
    CLOSE = auto()
    RESET = auto()


@dataclass
class SampleCtx:
    """Sample context for state machine tests."""

    value: str = ""
    history: list[str] = field(default_factory=list)


def test_state_machine_sync_transitions():
    """Test standard synchronous state transitions and handlers."""
    sm: StateMachine[SampleState, SampleEvent, SampleCtx] = StateMachine()

    @sm.transition(SampleState.DRAFT, SampleEvent.ACTIVATE, SampleState.ACTIVE)
    def on_activate(ctx: SampleCtx) -> None:
        ctx.value = "activated"
        ctx.history.append("draft->active")

    @sm.transition(
        from_state=[SampleState.ACTIVE, SampleState.DRAFT],
        event=SampleEvent.CLOSE,
        to_state=SampleState.CLOSED,
    )
    def on_close(ctx: SampleCtx) -> None:
        ctx.value = "closed"
        ctx.history.append("->closed")

    ctx = SampleCtx()
    state = SampleState.DRAFT

    state = sm.handle(ctx, state, SampleEvent.ACTIVATE)
    assert state == SampleState.ACTIVE
    assert ctx.value == "activated"
    assert ctx.history == ["draft->active"]

    state = sm.handle(ctx, state, SampleEvent.CLOSE)
    assert state == SampleState.CLOSED
    assert ctx.value == "closed"
    assert ctx.history == ["draft->active", "->closed"]


def test_invalid_transition_raises():
    """Test that illegal transitions raise InvalidTransition exception."""
    sm: StateMachine[SampleState, SampleEvent, SampleCtx] = StateMachine()

    @sm.transition(SampleState.DRAFT, SampleEvent.ACTIVATE, SampleState.ACTIVE)
    def on_activate(ctx: SampleCtx) -> None:
        pass

    ctx = SampleCtx()
    with pytest.raises(InvalidTransition) as exc_info:
        sm.handle(ctx, SampleState.CLOSED, SampleEvent.ACTIVATE)

    assert "No transition defined for state 'CLOSED' and event 'ACTIVATE'" in str(
        exc_info.value
    )


@pytest.mark.asyncio
async def test_state_machine_async_transitions():
    """Test asynchronous action handling using ahandle."""
    sm: StateMachine[SampleState, SampleEvent, SampleCtx] = StateMachine()

    @sm.transition(SampleState.DRAFT, SampleEvent.ACTIVATE, SampleState.ACTIVE)
    async def on_activate_async(ctx: SampleCtx) -> None:
        ctx.value = "async_activated"

    ctx = SampleCtx()
    next_state = await sm.ahandle(ctx, SampleState.DRAFT, SampleEvent.ACTIVATE)
    assert next_state == SampleState.ACTIVE
    assert ctx.value == "async_activated"
