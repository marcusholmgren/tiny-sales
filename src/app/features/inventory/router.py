"""API routes for managing inventory items and categories."""
import datetime
import logging
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional, List, Annotated

# Imports from this feature's modules
from .models import InventoryItem, Category
from .schemas import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    PaginatedInventoryResponse,
    CategoryResponse,
    CategoryCreate,
    CategoryUpdate
)
# For authentication - import User model for type hinting, and security function
from ..auth.models import User as AuthUser # Alias to avoid conflict if User is defined locally
from ..auth.security import get_current_active_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/inventory", # This prefix is already in app.main, but good for clarity here
    tags=["Inventory", "Categories"], # Combined tags
    responses={404: {"description": "Not found"}},
)

# Helper function (consider moving to service if it grows or is used elsewhere)
def _to_inventory_response(inventory_item: InventoryItem) -> InventoryItemResponse:
    # Ensure category is loaded, or handle it being None
    category_data = None
    if inventory_item.category: # Accessing .category directly might be problematic if not pre-fetched
                                # TortoisePy >0.9.0 allows direct access to loaded relations
        category_data = CategoryResponse.model_validate(inventory_item.category)

    return InventoryItemResponse(
        public_id=inventory_item.public_id,
        name=inventory_item.name,
        quantity=inventory_item.quantity,
        current_price=inventory_item.current_price,
        category=category_data,
        created_at=inventory_item.created_at,
        updated_at=inventory_item.updated_at
    )

def _to_category_response(category: Category) -> CategoryResponse:
    return CategoryResponse.model_validate(category)

@router.post(
    "/items/", # Changed to /items/ for clarity, full path /inventory/items/
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new inventory item",
    tags=["Inventory"]
)
async def create_inventory_item(
    item_in: InventoryItemCreate,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)]
):
    item_data = item_in.model_dump()
    category_public_id = item_data.pop("category_id", None)
    category_instance = None

    if category_public_id:
        category_instance = await Category.get_or_none(public_id=category_public_id)
        if not category_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with public_id {category_public_id} not found"
            )
    try:
        inventory_item = await InventoryItem.create(**item_data, category=category_instance)
        await inventory_item.fetch_related('category') # Ensure category is loaded for response
        return _to_inventory_response(inventory_item)
    except Exception as e:
        logger.error(f"Error creating inventory item: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create inventory item.")

@router.get(
    "/items/", # Changed to /items/
    response_model=PaginatedInventoryResponse,
    summary="List all active inventory items",
    tags=["Inventory"]
)
async def list_inventory_items(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    category_public_id: Optional[str] = Query(None, description="Public ID of the category to filter by")
):
    offset = (page - 1) * size
    filters = {"deleted_at__isnull": True}
    if category_public_id:
        category = await Category.get_or_none(public_id=category_public_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Category {category_public_id} not found")
        filters["category_id"] = category.id

    items_db = await InventoryItem.filter(**filters).prefetch_related('category').order_by('name').offset(offset).limit(size)
    total = await InventoryItem.filter(**filters).count()
    response_items = [_to_inventory_response(item) for item in items_db]
    return PaginatedInventoryResponse(items=response_items, total=total, page=page, size=size)

@router.get(
    "/items/{item_public_id}", # Changed to /items/{...}
    response_model=InventoryItemResponse,
    summary="Get a specific inventory item",
    tags=["Inventory"]
)
async def get_inventory_item(item_public_id: str):
    inventory_item = await InventoryItem.get_or_none(public_id=item_public_id, deleted_at__isnull=True)
    if not inventory_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await inventory_item.fetch_related('category')
    return _to_inventory_response(inventory_item)

@router.put(
    "/items/{item_public_id}", # Changed to /items/{...}
    response_model=InventoryItemResponse,
    summary="Update an inventory item",
    tags=["Inventory"]
)
async def update_inventory_item(
    item_public_id: str,
    item_in: InventoryItemUpdate,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)]
):
    inventory_item = await InventoryItem.get_or_none(public_id=item_public_id, deleted_at__isnull=True)
    if not inventory_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    update_data = item_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields for update")

    category_public_id = update_data.pop("category_id", "NOT_SET")
    if category_public_id != "NOT_SET":
        if category_public_id is None:
            inventory_item.category = None
        else:
            cat = await Category.get_or_none(public_id=category_public_id)
            if not cat:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Category {category_public_id} not found")
            inventory_item.category = cat

    for key, value in update_data.items():
        setattr(inventory_item, key, value)
    await inventory_item.save()
    await inventory_item.fetch_related('category')
    return _to_inventory_response(inventory_item)

@router.delete(
    "/items/{item_public_id}", # Changed to /items/{...}
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete an inventory item",
    tags=["Inventory"]
)
async def delete_inventory_item(
    item_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)]
):
    inventory_item = await InventoryItem.get_or_none(public_id=item_public_id, deleted_at__isnull=True)
    if not inventory_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found or already deleted")
    inventory_item.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    await inventory_item.save()
    return None

# --- Category Endpoints ---
@router.post(
    "/categories/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new category",
    tags=["Categories"]
)
async def create_category(
    category_in: CategoryCreate,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)]
):
    try:
        category = await Category.create(**category_in.model_dump())
        return _to_category_response(category)
    except Exception as e:
        logger.error(f"Error creating category: {e}", exc_info=True)
        if "UNIQUE constraint failed" in str(e):
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Category name '{category_in.name}' already exists.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create category.")

@router.get(
    "/categories/",
    response_model=List[CategoryResponse],
    summary="List all categories",
    tags=["Categories"]
)
async def list_categories():
    categories = await Category.all().order_by('name')
    return [_to_category_response(cat) for cat in categories]

@router.get(
    "/categories/{category_public_id}",
    response_model=CategoryResponse,
    summary="Get a specific category",
    tags=["Categories"]
)
async def get_category(category_public_id: str):
    category = await Category.get_or_none(public_id=category_public_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return _to_category_response(category)

@router.put(
    "/categories/{category_public_id}",
    response_model=CategoryResponse,
    summary="Update a category",
    tags=["Categories"]
)
async def update_category(
    category_public_id: str,
    category_in: CategoryUpdate,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)]
):
    category = await Category.get_or_none(public_id=category_public_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    update_data = category_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields for update")
    for key, value in update_data.items():
        setattr(category, key, value)
    try:
        await category.save()
        return _to_category_response(category)
    except Exception as e:
        logger.error(f"Error updating category: {e}", exc_info=True)
        if "UNIQUE constraint failed" in str(e):
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Category name '{category_in.name}' already exists.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update category.")

@router.delete(
    "/categories/{category_public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
    tags=["Categories"]
)
async def delete_category(
    category_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)]
):
    category = await Category.get_or_none(public_id=category_public_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    await category.delete() # SET_NULL on InventoryItem.category handles relations
    return None
