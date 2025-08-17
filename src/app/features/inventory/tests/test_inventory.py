
import pytest
from fastapi import HTTPException
from app.features.inventory.service import (
    create_category,
    get_category,
    list_categories,
    update_category,
    delete_category,
    create_inventory_item,
    get_inventory_item,
    list_inventory_items,
    update_inventory_item,
    delete_inventory_item,
)
from app.features.inventory.schemas import (
    CategoryCreate,
    CategoryUpdate,
    InventoryItemCreate,
    InventoryItemUpdate,
)
from app.features.inventory.models import Category, InventoryItem

@pytest.mark.asyncio
async def test_create_category():
    """Test creating a category."""
    category_in = CategoryCreate(name="Test Category", description="A test category")
    created_category = await create_category(category_in)
    assert created_category.name == category_in.name
    assert created_category.description == category_in.description
    db_category = await Category.get(public_id=created_category.public_id)
    assert db_category is not None


@pytest.mark.asyncio
async def test_create_category_duplicate_name():
    """Test creating a category with a duplicate name."""
    category_in = CategoryCreate(name="Duplicate Category", description="A test category")
    await create_category(category_in)
    with pytest.raises(HTTPException) as exc_info:
        await create_category(category_in)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_get_category(default_category: Category):
    """Test getting a category."""
    fetched_category = await get_category(default_category.public_id)
    assert fetched_category.public_id == default_category.public_id
    assert fetched_category.name == default_category.name


@pytest.mark.asyncio
async def test_get_category_not_found():
    """Test getting a non-existent category."""
    with pytest.raises(HTTPException) as exc_info:
        await get_category("non-existent-id")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_list_categories(default_category: Category, another_category: Category):
    """Test listing categories."""
    categories = await list_categories()
    assert len(categories) >= 2
    assert any(c.public_id == default_category.public_id for c in categories)
    assert any(c.public_id == another_category.public_id for c in categories)


@pytest.mark.asyncio
async def test_update_category(default_category: Category):
    """Test updating a category."""
    update_data = CategoryUpdate(name="Updated Name", description="Updated description")
    updated_category = await update_category(default_category.public_id, update_data)
    assert updated_category.name == "Updated Name"
    assert updated_category.description == "Updated description"
    db_category = await Category.get(public_id=default_category.public_id)
    assert db_category.name == "Updated Name"


@pytest.mark.asyncio
async def test_update_category_not_found():
    """Test updating a non-existent category."""
    update_data = CategoryUpdate(name="Updated Name")
    with pytest.raises(HTTPException) as exc_info:
        await update_category("non-existent-id", update_data)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_category(default_category: Category):
    """Test deleting a category."""
    await delete_category(default_category.public_id)
    with pytest.raises(HTTPException) as exc_info:
        await get_category(default_category.public_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_not_found():
    """Test deleting a non-existent category."""
    with pytest.raises(HTTPException) as exc_info:
        await delete_category("non-existent-id")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_inventory_item(default_category: Category):
    """Test creating an inventory item."""
    item_in = InventoryItemCreate(
        name="Test Item",
        quantity=10,
        current_price=99.99,
        category_id=default_category.public_id,
    )
    created_item = await create_inventory_item(item_in)
    assert created_item.name == item_in.name
    assert created_item.category.public_id == default_category.public_id
    db_item = await InventoryItem.get(public_id=created_item.public_id)
    assert db_item is not None


@pytest.mark.asyncio
async def test_create_inventory_item_no_category():
    """Test creating an inventory item without a category."""
    item_in = InventoryItemCreate(
        name="Test Item No Cat", quantity=5, current_price=50.0
    )
    created_item = await create_inventory_item(item_in)
    assert created_item.name == item_in.name
    assert created_item.category is None


@pytest.mark.asyncio
async def test_get_inventory_item(sample_inventory: list[InventoryItem]):
    """Test getting an inventory item."""
    item_to_fetch = sample_inventory[0]
    fetched_item = await get_inventory_item(item_to_fetch.public_id)
    assert fetched_item.public_id == item_to_fetch.public_id
    assert fetched_item.name == item_to_fetch.name


@pytest.mark.asyncio
async def test_get_inventory_item_not_found():
    """Test getting a non-existent inventory item."""
    with pytest.raises(HTTPException) as exc_info:
        await get_inventory_item("non-existent-id")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_list_inventory_items(sample_inventory: list[InventoryItem]):
    """Test listing inventory items."""
    paginated_response = await list_inventory_items(page=1, size=10, category_public_id=None)
    assert paginated_response.total >= len(sample_inventory)
    assert paginated_response.page == 1
    assert paginated_response.size == 10


@pytest.mark.asyncio
async def test_list_inventory_items_by_category(
    inventory_item_factory, default_category, another_category
):
    """Test listing inventory items filtered by category."""
    await inventory_item_factory("Item 1", category=default_category)
    await inventory_item_factory("Item 2", category=another_category)
    await inventory_item_factory("Item 3", category=default_category)

    paginated_response = await list_inventory_items(
        page=1, size=10, category_public_id=default_category.public_id
    )
    assert paginated_response.total == 2
    for item in paginated_response.items:
        assert item.category.public_id == default_category.public_id


@pytest.mark.asyncio
async def test_update_inventory_item(sample_inventory: list[InventoryItem]):
    """Test updating an inventory item."""
    item_to_update = sample_inventory[0]
    update_data = InventoryItemUpdate(name="Updated Item Name", quantity=99)
    updated_item = await update_inventory_item(item_to_update.public_id, update_data)
    assert updated_item.name == "Updated Item Name"
    assert updated_item.quantity == 99
    db_item = await InventoryItem.get(public_id=item_to_update.public_id)
    assert db_item.name == "Updated Item Name"
    assert db_item.quantity == 99


@pytest.mark.asyncio
async def test_update_inventory_item_not_found():
    """Test updating a non-existent inventory item."""
    update_data = InventoryItemUpdate(name="Won't work")
    with pytest.raises(HTTPException) as exc_info:
        await update_inventory_item("non-existent-id", update_data)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_inventory_item(sample_inventory: list[InventoryItem]):
    """Test deleting an inventory item."""
    item_to_delete = sample_inventory[0]
    await delete_inventory_item(item_to_delete.public_id)
    db_item = await InventoryItem.get_or_none(public_id=item_to_delete.public_id)
    assert db_item.deleted_at is not None

    # Check that it's not returned by get
    with pytest.raises(HTTPException) as exc_info:
        await get_inventory_item(item_to_delete.public_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_inventory_item_not_found():
    """Test deleting a non-existent inventory item."""
    with pytest.raises(HTTPException) as exc_info:
        await delete_inventory_item("non-existent-id")
    assert exc_info.value.status_code == 404
