"""Command objects and handlers for inventory and category operations."""

from dataclasses import dataclass
from typing import List, Optional

from app.common.commands import BaseCommand, CommandHandler
from . import schemas, service


# --- Inventory Commands & Handlers ---


@dataclass
class CreateInventoryItemCommand(BaseCommand):
    """Command payload for creating an inventory item."""

    item_in: schemas.InventoryItemCreate


class CreateInventoryItemCommandHandler(
    CommandHandler[CreateInventoryItemCommand, schemas.InventoryItemResponse]
):
    """Command handler for creating a new inventory item."""

    async def execute(
        self, command: CreateInventoryItemCommand
    ) -> schemas.InventoryItemResponse:
        """Executes inventory item creation.

        Args:
            command: The command containing the item creation data.

        Returns:
            InventoryItemResponse: The created inventory item.
        """
        return await service.create_inventory_item(command.item_in)


@dataclass
class ListInventoryItemsCommand(BaseCommand):
    """Command payload for listing paginated inventory items."""

    limit: int = 10
    cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    category_public_id: Optional[str] = None


class ListInventoryItemsCommandHandler(
    CommandHandler[ListInventoryItemsCommand, schemas.PaginatedInventoryResponse]
):
    """Command handler for retrieving a paginated list of active inventory items."""

    async def execute(
        self, command: ListInventoryItemsCommand
    ) -> schemas.PaginatedInventoryResponse:
        """Executes inventory items retrieval.

        Args:
            command: The command containing pagination and filter query parameters.

        Returns:
            PaginatedInventoryResponse: Paginated result set of inventory items.
        """
        return await service.list_inventory_items(
            limit=command.limit,
            cursor=command.cursor,
            prev_cursor=command.prev_cursor,
            category_public_id=command.category_public_id,
        )


@dataclass
class GetInventoryItemCommand(BaseCommand):
    """Command payload for retrieving a specific inventory item by ID."""

    item_public_id: str


class GetInventoryItemCommandHandler(
    CommandHandler[GetInventoryItemCommand, schemas.InventoryItemResponse]
):
    """Command handler for fetching an inventory item by public ID."""

    async def execute(
        self, command: GetInventoryItemCommand
    ) -> schemas.InventoryItemResponse:
        """Executes single inventory item retrieval.

        Args:
            command: The command containing the item's public ID.

        Returns:
            InventoryItemResponse: The retrieved inventory item.
        """
        return await service.get_inventory_item(command.item_public_id)


@dataclass
class UpdateInventoryItemCommand(BaseCommand):
    """Command payload for updating an inventory item."""

    item_public_id: str
    item_in: schemas.InventoryItemUpdate


class UpdateInventoryItemCommandHandler(
    CommandHandler[UpdateInventoryItemCommand, schemas.InventoryItemResponse]
):
    """Command handler for updating an inventory item."""

    async def execute(
        self, command: UpdateInventoryItemCommand
    ) -> schemas.InventoryItemResponse:
        """Executes inventory item update.

        Args:
            command: The command containing update data and item ID.

        Returns:
            InventoryItemResponse: The updated inventory item.
        """
        return await service.update_inventory_item(
            command.item_public_id, command.item_in
        )


@dataclass
class DeleteInventoryItemCommand(BaseCommand):
    """Command payload for soft-deleting an inventory item."""

    item_public_id: str


class DeleteInventoryItemCommandHandler(
    CommandHandler[DeleteInventoryItemCommand, None]
):
    """Command handler for deleting an inventory item."""

    async def execute(self, command: DeleteInventoryItemCommand) -> None:
        """Executes soft-deletion of an inventory item.

        Args:
            command: The command containing item public ID.
        """
        await service.delete_inventory_item(command.item_public_id)


# --- Category Commands & Handlers ---


@dataclass
class CreateCategoryCommand(BaseCommand):
    """Command payload for creating a category."""

    category_in: schemas.CategoryCreate


class CreateCategoryCommandHandler(
    CommandHandler[CreateCategoryCommand, schemas.CategoryResponse]
):
    """Command handler for creating a category."""

    async def execute(
        self, command: CreateCategoryCommand
    ) -> schemas.CategoryResponse:
        """Executes category creation.

        Args:
            command: The command containing category creation payload.

        Returns:
            CategoryResponse: The created category details.
        """
        return await service.create_category(command.category_in)


@dataclass
class ListCategoriesCommand(BaseCommand):
    """Command payload for listing all categories."""

    pass


class ListCategoriesCommandHandler(
    CommandHandler[ListCategoriesCommand, List[schemas.CategoryResponse]]
):
    """Command handler for retrieving all categories."""

    async def execute(
        self, command: ListCategoriesCommand
    ) -> List[schemas.CategoryResponse]:
        """Executes category listing.

        Args:
            command: The ListCategoriesCommand instance.

        Returns:
            List[CategoryResponse]: List of all active categories.
        """
        return await service.list_categories()


@dataclass
class GetCategoryCommand(BaseCommand):
    """Command payload for retrieving a specific category."""

    category_public_id: str


class GetCategoryCommandHandler(
    CommandHandler[GetCategoryCommand, schemas.CategoryResponse]
):
    """Command handler for fetching a category by public ID."""

    async def execute(self, command: GetCategoryCommand) -> schemas.CategoryResponse:
        """Executes category retrieval.

        Args:
            command: The command containing category public ID.

        Returns:
            CategoryResponse: The retrieved category.
        """
        return await service.get_category(command.category_public_id)


@dataclass
class UpdateCategoryCommand(BaseCommand):
    """Command payload for updating a category."""

    category_public_id: str
    category_in: schemas.CategoryUpdate


class UpdateCategoryCommandHandler(
    CommandHandler[UpdateCategoryCommand, schemas.CategoryResponse]
):
    """Command handler for updating a category."""

    async def execute(
        self, command: UpdateCategoryCommand
    ) -> schemas.CategoryResponse:
        """Executes category update.

        Args:
            command: The command containing category update details and ID.

        Returns:
            CategoryResponse: The updated category response.
        """
        return await service.update_category(
            command.category_public_id, command.category_in
        )


@dataclass
class DeleteCategoryCommand(BaseCommand):
    """Command payload for deleting a category."""

    category_public_id: str


class DeleteCategoryCommandHandler(CommandHandler[DeleteCategoryCommand, None]):
    """Command handler for deleting a category."""

    async def execute(self, command: DeleteCategoryCommand) -> None:
        """Executes category deletion.

        Args:
            command: The command containing category public ID.
        """
        await service.delete_category(command.category_public_id)
