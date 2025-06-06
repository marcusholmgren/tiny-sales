from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "inventory_items" ADD "current_price" REAL NOT NULL DEFAULT 0 /* Current price of the inventory item */;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "inventory_items" DROP COLUMN "current_price";"""
