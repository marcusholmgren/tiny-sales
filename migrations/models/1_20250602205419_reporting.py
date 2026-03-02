from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "inventory_items" ADD "current_price" REAL NOT NULL DEFAULT 0 /* Current price of the inventory item */;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "inventory_items" DROP COLUMN "current_price";"""


MODELS_STATE = (
    "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"
)
