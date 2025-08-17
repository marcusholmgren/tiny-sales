"""API routes for managing inventory items and categories."""
from fastapi import APIRouter, status, Query, Depends
from typing import Optional, List, Annotated

from .schemas import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    PaginatedInventoryResponse,
    CategoryResponse,
    CategoryCreate,
    CategoryUpdate,
)
from . import service

# For authentication - import User model for type hinting, and security function
from ..auth.models import (
    User as AuthUser,
)
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
):
    return await service.create_inventory_item(item_in)


@router.get(
    "/items/",
    response_model=PaginatedInventoryResponse,
    summary="List all active inventory items",
    tags=["Inventory"],
)
async def list_inventory_items(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    category_public_id: Optional[str] = Query(
        None, description="Public ID of the category to filter by"
    ),
):
    return await service.list_inventory_items(page, size, category_public_id)


@router.get(
    "/items/{item_public_id}",
    response_model=InventoryItemResponse,
    summary="Get a specific inventory item",
    tags=["Inventory"],
)
async def get_inventory_item(item_public_id: str):
    return await service.get_inventory_item(item_public_id)


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
):
    return await service.update_inventory_item(item_public_id, item_in)


@router.delete(
    "/items/{item_public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete an inventory item",
    tags=["Inventory"],
)
async def delete_inventory_item(
    item_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
):
    await service.delete_inventory_item(item_public_id)
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
):
    return await service.create_category(category_in)


@router.get(
    "/categories/",
    response_model=List[CategoryResponse],
    summary="List all categories",
    tags=["Categories"],
)
async def list_categories():
    return await service.list_categories()


@router.get(
    "/categories/{category_public_id}",
    response_model=CategoryResponse,
    summary="Get a specific category",
    tags=["Categories"],
)
async def get_category(category_public_id: str):
    return await service.get_category(category_public_id)


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
):
    return await service.update_category(category_public_id, category_in)


@router.delete(
    "/categories/{category_public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
    tags=["Categories"],
)
async def delete_category(
    category_public_id: str,
    current_admin: Annotated[AuthUser, Depends(get_current_active_admin_user)],
):
    await service.delete_category(category_public_id)
    return None
