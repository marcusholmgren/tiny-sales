"""Unit tests for BaseCommand and CommandHandler."""

from dataclasses import FrozenInstanceError, dataclass
import pytest

from app.common.commands import BaseCommand, CommandHandler

pytestmark = pytest.mark.asyncio


@dataclass(frozen=True, slots=True)
class SampleCommand(BaseCommand):
    """Sample command for testing."""

    name: str
    value: int = 42


class SampleCommandHandler(CommandHandler[SampleCommand, str]):
    """Sample handler for testing."""

    async def execute(self, command: SampleCommand) -> str:
        return f"{command.name}:{command.value}"


async def test_base_command_immutability_and_slots():
    """Verify BaseCommand subclasses are frozen and slotted without __dict__."""
    cmd = SampleCommand(name="test_cmd")
    assert cmd.name == "test_cmd"
    assert cmd.value == 42
    assert not hasattr(cmd, "__dict__")

    with pytest.raises(FrozenInstanceError):
        cmd.name = "new_name"  # type: ignore[misc]


async def test_command_handler_execution():
    """Verify CommandHandler can be invoked as a callable and via execute()."""
    handler = SampleCommandHandler()
    cmd = SampleCommand(name="action", value=100)

    # Callable syntax
    result_call = await handler(cmd)
    assert result_call == "action:100"

    # Execute syntax
    result_execute = await handler.execute(cmd)
    assert result_execute == "action:100"


async def test_command_handler_abstract_enforcement():
    """Verify CommandHandler cannot be instantiated without implementing execute."""

    class IncompleteHandler(CommandHandler[SampleCommand, str]):
        pass

    with pytest.raises(TypeError):
        IncompleteHandler()  # type: ignore[abstract]
