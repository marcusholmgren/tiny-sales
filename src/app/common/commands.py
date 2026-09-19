"""Base interfaces and generic definitions for the Command Pattern.

This module provides foundational classes and generic interfaces for implementing
the Command Pattern across features.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BaseCommand:
    """Base marker class for immutable command objects carrying execution payload."""

    pass


class CommandHandler[CommandT: BaseCommand, ResultT](ABC):
    """Abstract base class for command handlers.

    Command handlers encapsulate business operation execution for a given command.
    Handlers can be invoked directly as callables (`await handler(command)`)
    or via `execute()` (`await handler.execute(command)`).
    """

    @abstractmethod
    async def execute(self, command: CommandT) -> ResultT:
        """Executes the specified command.

        Args:
            command: The command object containing parameter payload.

        Returns:
            ResultT: The result of processing the command.
        """
        ...

    async def __call__(self, command: CommandT) -> ResultT:
        """Invokes the command handler as a callable."""
        return await self.execute(command)
