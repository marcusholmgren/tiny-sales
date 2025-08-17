import pytest_asyncio
from app.features.inventory.models import Category, InventoryItem


@pytest_asyncio.fixture
async def default_category() -> Category:
    """A default category that can be used in tests."""
    category = await Category.create(name="Default Category", description="A default category")
    return category


@pytest_asyncio.fixture
async def another_category() -> Category:
    """Another category that can be used in tests."""
    category = await Category.create(name="Another Category", description="Another category")
    return category


@pytest_asyncio.fixture
async def inventory_item_factory(default_category: Category):
    """A factory to create inventory items."""

    async def _factory(
        name: str,
        quantity: int = 10,
        price: float = 100.0,
        category: Category = default_category,
    ):
        item = await InventoryItem.create(
            name=name,
            quantity=quantity,
            current_price=price,
            category=category,
        )
        return item

    return _factory


@pytest_asyncio.fixture
async def sample_inventory(inventory_item_factory):
    """A list of sample inventory items."""
    items = [
        await inventory_item_factory(name="Sample Item 1"),
        await inventory_item_factory(name="Sample Item 2"),
        await inventory_item_factory(name="Sample Item 3"),
    ]
    return items