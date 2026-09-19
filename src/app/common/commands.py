"""Base interfaces and generic definitions for the Command Pattern.

This module provides foundational classes and generic interfaces for implementing
the Command Pattern across features.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

CommandT = TypeVar("CommandT")
ResultT = TypeVar("ResultT")


class BaseCommand:
    """Base marker class for command objects carrying execution input data."""

    pass


class CommandHandler(ABC, Generic[CommandT, ResultT]):
    """Abstract base class for command handlers.

    Command handlers encapsulate business operation execution for a given command.
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
