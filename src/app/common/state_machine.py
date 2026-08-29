"""Generic finite state machine implementation."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar, Any

# Type variables for State (S), Event (E), and Context (C)
S = TypeVar("S", bound=Enum)
E = TypeVar("E", bound=Enum)
C = TypeVar("C")

Action = Callable[[C], Any]


class InvalidTransition(Exception):
    """Raised when an event is triggered that has no transition from the current state."""

    pass


@dataclass
class StateMachine[S: Enum, E: Enum, C]:
    """A generic, table-driven finite state machine.

    Type Parameters:
        S: Enum representing valid states.
        E: Enum representing transition events.
        C: Context object containing mutable business data.
    """

    transitions: dict[tuple[S, E], tuple[S, Action[C]]] = field(default_factory=dict)

    def add_transition(
        self, from_state: S, event: E, to_state: S, action: Action[C]
    ) -> None:
        """Register a single state transition mapping and its associated action."""
        self.transitions[(from_state, event)] = (to_state, action)

    def next_transition(self, state: S, event: E) -> tuple[S, Action[C]]:
        """Look up target state and action for a given (state, event) pair."""
        try:
            return self.transitions[(state, event)]
        except KeyError:
            raise InvalidTransition(
                f"No transition defined for state '{state.name}' and event '{event.name}'"
            )

    def handle(self, ctx: C, state: S, event: E) -> S:
        """Execute the action associated with the transition and return the new state.

        If the action raises an exception, the state change does not complete.
        """
        next_state, action = self.next_transition(state, event)
        action(ctx)
        return next_state

    async def ahandle(self, ctx: C, state: S, event: E) -> S:
        """Execute the action associated with the transition (supporting async actions) and return the new state.

        If the action raises an exception, the state change does not complete.
        """
        import inspect

        next_state, action = self.next_transition(state, event)
        if inspect.iscoroutinefunction(action):
            await action(ctx)
        else:
            res = action(ctx)
            if inspect.isawaitable(res):
                await res
        return next_state

    def transition(
        self, from_state: S | Sequence[S], event: E, to_state: S
    ) -> Callable[[Action[C]], Action[C]]:
        """Decorator to register a transition handler for one or more source states."""
        states = (
            list(from_state)
            if isinstance(from_state, (list, tuple, set))
            else [from_state]
        )

        def decorator(action: Action[C]) -> Action[C]:
            for s in states:
                self.add_transition(s, event, to_state, action)
            return action

        return decorator
