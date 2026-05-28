import datetime
import logging
from decimal import Decimal
from typing import Optional, List
from fastapi import HTTPException, status
from ...common import MoneySchema
from .models import InventoryItem, Category
from .schemas import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    PaginatedInventoryResponse,
    CategoryResponse,
    CategoryCreate,
    CategoryUpdate,
)

logger = logging.getLogger(__name__)


def _to_inventory_response(inventory_item: InventoryItem) -> InventoryItemResponse:
    """Converts an InventoryItem model instance to an InventoryItemResponse schema."""
    category_data = None
    if inventory_item.category:
        category_data = CategoryResponse.model_validate(inventory_item.category)

    return InventoryItemResponse(
        public_id=inventory_item.public_id,
        name=inventory_item.name,
        quantity=inventory_item.quantity,
        current_price=MoneySchema(
            amount=inventory_item.current_price.amount,
            currency=inventory_item.current_price.currency.code
        ),
        category=category_data,
        created_at=inventory_item.created_at,
        updated_at=inventory_item.updated_at,
    )


async def create_inventory_item(item_in: InventoryItemCreate) -> InventoryItemResponse:
    """
    Creates a new inventory item.

    Args:
        item_in: The data for the new inventory item.

    Returns:
        The created inventory item.
    """
    item_data = item_in.model_dump()
    category_public_id = item_data.pop("category_id", None)
    current_price_data = item_data.pop("current_price", None)

    price_amount = Decimal("0.0000")
    price_currency = "SEK"
    if current_price_data:
        price_amount = current_price_data["amount"]
        price_currency = current_price_data["currency"]

    category_instance = None

    if category_public_id:
        category_instance = await Category.get_or_none(public_id=category_public_id)
        if not category_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with public_id {category_public_id} not found",
            )
    inventory_item = await InventoryItem.create(
        **item_data,
        category=category_instance,
        price_amount=price_amount,
        price_currency=price_currency,
    )
    await inventory_item.fetch_related("category")
    return _to_inventory_response(inventory_item)


async def list_inventory_items(
    page: int, size: int, category_public_id: Optional[str]
) -> PaginatedInventoryResponse:
    """
    Lists all active inventory items.

    Args:
        page: The page number.
        size: The number of items per page.
        category_public_id: The public ID of the category to filter by.

    Returns:
        A paginated list of inventory items.
    """
    offset = (page - 1) * size
    filters = {"deleted_at__isnull": True}
    if category_public_id:
        category = await Category.get_or_none(public_id=category_public_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category {category_public_id} not found",
            )
        filters["category_id"] = category.id

    items_db = (
        await InventoryItem.filter(**filters)
        .prefetch_related("category")
        .order_by("name")
        .offset(offset)
        .limit(size)
    )
    total = await InventoryItem.filter(**filters).count()
    response_items = [_to_inventory_response(item) for item in items_db]
    return PaginatedInventoryResponse(
        items=response_items, total=total, page=page, size=size
    )


async def get_inventory_item(item_public_id: str) -> InventoryItemResponse:
    """
    Gets a specific inventory item.

    Args:
        item_public_id: The public ID of the inventory item.

    Returns:
        The inventory item.
    """
    inventory_item = await InventoryItem.get_or_none(
        public_id=item_public_id, deleted_at__isnull=True
    )
    if not inventory_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    await inventory_item.fetch_related("category")
    return _to_inventory_response(inventory_item)


async def update_inventory_item(
    item_public_id: str, item_in: InventoryItemUpdate
) -> InventoryItemResponse:
    """
    Updates an inventory item.

    Args:
        item_public_id: The public ID of the inventory item to update.
        item_in: The new data for the inventory item.

    Returns:
        The updated inventory item.
    """
    inventory_item = await InventoryItem.get_or_none(
        public_id=item_public_id, deleted_at__isnull=True
    )
    if not inventory_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )

    update_data = item_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields for update"
        )

    if "current_price" in update_data:
        price_data = update_data.pop("current_price")
        if price_data:
            inventory_item.price_amount = Decimal(str(price_data["amount"]))
            inventory_item.price_currency = price_data["currency"]

    if "category_id" in update_data:
        category_public_id = update_data.pop("category_id")
        if category_public_id:
            category = await Category.get_or_none(public_id=category_public_id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category with public_id {category_public_id} not found",
                )
            inventory_item.category = category
        else:
            inventory_item.category = None

    for key, value in update_data.items():
        setattr(inventory_item, key, value)
    await inventory_item.save()
    await inventory_item.fetch_related("category")
    return _to_inventory_response(inventory_item)


async def delete_inventory_item(item_public_id: str):
    """
    Soft deletes an inventory item.

    Args:
        item_public_id: The public ID of the inventory item to delete.
    """
    inventory_item = await InventoryItem.get_or_none(
        public_id=item_public_id, deleted_at__isnull=True
    )
    if not inventory_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found or already deleted",
        )
    inventory_item.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    await inventory_item.save()
    return None


def _to_category_response(category: Category) -> CategoryResponse:
    """Converts a Category model instance to a CategoryResponse schema."""
    return CategoryResponse.model_validate(category)


async def create_category(category_in: CategoryCreate) -> CategoryResponse:
    """
    Creates a new category.

    Args:
        category_in: The data for the new category.

    Returns:
        The created category.
    """
    existing_category = await Category.get_or_none(name=category_in.name)
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category name '{category_in.name}' already exists.",
        )
    category = await Category.create(**category_in.model_dump())
    return _to_category_response(category)


async def list_categories() -> List[CategoryResponse]:
    """
    Lists all categories.

    Returns:
        A list of all categories.
    """
    categories = await Category.all().order_by("name")
    return [_to_category_response(cat) for cat in categories]


async def get_category(category_public_id: str) -> CategoryResponse:
    """
    Gets a specific category.

    Args:
        category_public_id: The public ID of the category.

    Returns:
        The category.
    """
    category = await Category.get_or_none(public_id=category_public_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return _to_category_response(category)


async def update_category(
    category_public_id: str, category_in: CategoryUpdate
) -> CategoryResponse:
    """
    Updates a category.

    Args:
        category_public_id: The public ID of the category to update.
        category_in: The new data for the category.

    Returns:
        The updated category.
    """
    category = await Category.get_or_none(public_id=category_public_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    update_data = category_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields for update"
        )
    for key, value in update_data.items():
        setattr(category, key, value)
    try:
        await category.save()
        return _to_category_response(category)
    except Exception as e:
        logger.error(f"Error updating category: {e}", exc_info=True)
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category name '{category_in.name}' already exists.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category.",
        )


async def delete_category(category_public_id: str):
    """
    Deletes a category.

    Args:
        category_public_id: The public ID of the category to delete.
    """
    category = await Category.get_or_none(public_id=category_public_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    await category.delete()
    return None
