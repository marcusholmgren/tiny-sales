"""API routes for managing inventory items and categories, using command handlers."""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, status

from .commands import (
    CreateCategoryCommand,
    CreateCategoryCommandHandler,
    CreateInventoryItemCommand,
    CreateInventoryItemCommandHandler,
    DeleteCategoryCommand,
    DeleteCategoryCommandHandler,
    DeleteInventoryItemCommand,
    DeleteInventoryItemCommandHandler,
    GetCategoryCommand,
    GetCategoryCommandHandler,
    GetInventoryItemCommand,
    GetInventoryItemCommandHandler,
    ListCategoriesCommand,
    ListCategoriesCommandHandler,
    ListInventoryItemsCommand,
    ListInventoryItemsCommandHandler,
    UpdateCategoryCommand,
    UpdateCategoryCommandHandler,
    UpdateInventoryItemCommand,
    UpdateInventoryItemCommandHandler,
)
from .schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    PaginatedInventoryResponse,
)

# For authentication - import User model for type hinting, and security function
from ..auth.models import User as AuthUser
from ..auth.security import get_current_active_admin_user

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory", "Categories"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/items/",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new inventory item",
    tags=["Inventory"],
)
async def create_inventory_item(
    item_in: InventoryItemCreate,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[CreateInventoryItemCommandHandler, Depends()],
):
    """Creates a new inventory item.

    Requires admin privileges.
    """
    command = CreateInventoryItemCommand(item_in=item_in)
    return await handler.execute(command)


@router.get(
    "/items/",
    response_model=PaginatedInventoryResponse,
    summary="List all active inventory items",
    tags=["Inventory"],
)
async def list_inventory_items(
    handler: Annotated[ListInventoryItemsCommandHandler, Depends()],
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    cursor: Optional[str] = Query(None, description="Forward cursor for pagination"),
    prev_cursor: Optional[str] = Query(
        None, description="Backward cursor for pagination"
    ),
    category_public_id: Optional[str] = Query(
        None, description="Public ID of the category to filter by"
    ),
):
    """Retrieves a cursor-paginated list of active inventory items.

    Can be filtered by category.
    """
    command = ListInventoryItemsCommand(
        limit=limit,
        cursor=cursor,
        prev_cursor=prev_cursor,
        category_public_id=category_public_id,
    )
    return await handler.execute(command)


@router.get(
    "/items/{item_public_id}",
    response_model=InventoryItemResponse,
    summary="Get a specific inventory item",
    tags=["Inventory"],
)
async def get_inventory_item(
    item_public_id: str,
    handler: Annotated[GetInventoryItemCommandHandler, Depends()],
):
    """Retrieves a single inventory item by its public ID."""
    command = GetInventoryItemCommand(item_public_id=item_public_id)
    return await handler.execute(command)


@router.put(
    "/items/{item_public_id}",
    response_model=InventoryItemResponse,
    summary="Update an inventory item",
    tags=["Inventory"],
)
async def update_inventory_item(
    item_public_id: str,
    item_in: InventoryItemUpdate,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[UpdateInventoryItemCommandHandler, Depends()],
):
    """Updates an existing inventory item.

    Requires admin privileges.
    """
    command = UpdateInventoryItemCommand(
        item_public_id=item_public_id, item_in=item_in
    )
    return await handler.execute(command)


@router.delete(
    "/items/{item_public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete an inventory item",
    tags=["Inventory"],
)
async def delete_inventory_item(
    item_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[DeleteInventoryItemCommandHandler, Depends()],
):
    """Soft deletes an inventory item.

    Requires admin privileges.
    """
    command = DeleteInventoryItemCommand(item_public_id=item_public_id)
    await handler.execute(command)
    return None


# --- Category Endpoints ---
@router.post(
    "/categories/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new category",
    tags=["Categories"],
)
async def create_category(
    category_in: CategoryCreate,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[CreateCategoryCommandHandler, Depends()],
):
    """Creates a new category.

    Requires admin privileges.
    """
    command = CreateCategoryCommand(category_in=category_in)
    return await handler.execute(command)


@router.get(
    "/categories/",
    response_model=List[CategoryResponse],
    summary="List all categories",
    tags=["Categories"],
)
async def list_categories(
    handler: Annotated[ListCategoriesCommandHandler, Depends()],
):
    """Retrieves a list of all categories."""
    command = ListCategoriesCommand()
    return await handler.execute(command)


@router.get(
    "/categories/{category_public_id}",
    response_model=CategoryResponse,
    summary="Get a specific category",
    tags=["Categories"],
)
async def get_category(
    category_public_id: str,
    handler: Annotated[GetCategoryCommandHandler, Depends()],
):
    """Retrieves a single category by its public ID."""
    command = GetCategoryCommand(category_public_id=category_public_id)
    return await handler.execute(command)


@router.put(
    "/categories/{category_public_id}",
    response_model=CategoryResponse,
    summary="Update a category",
    tags=["Categories"],
)
async def update_category(
    category_public_id: str,
    category_in: CategoryUpdate,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[UpdateCategoryCommandHandler, Depends()],
):
    """Updates an existing category.

    Requires admin privileges.
    """
    command = UpdateCategoryCommand(
        category_public_id=category_public_id, category_in=category_in
    )
    return await handler.execute(command)


@router.delete(
    "/categories/{category_public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
    tags=["Categories"],
)
async def delete_category(
    category_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
    handler: Annotated[DeleteCategoryCommandHandler, Depends()],
):
    """Deletes a category.

    Requires admin privileges.
    """
    command = DeleteCategoryCommand(category_public_id=category_public_id)
    await handler.execute(command)
    return None
