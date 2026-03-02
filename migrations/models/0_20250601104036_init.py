from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "categories" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "public_id" VARCHAR(27) NOT NULL UNIQUE,
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "description" TEXT
);
CREATE INDEX IF NOT EXISTS "idx_categories_public__17405c" ON "categories" ("public_id");
CREATE TABLE IF NOT EXISTS "inventory_items" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "public_id" VARCHAR(27) NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL,
    "quantity" INT NOT NULL DEFAULT 0,
    "deleted_at" TIMESTAMP,
    "category_id" INT REFERENCES "categories" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_inventory_i_public__7c6581" ON "inventory_items" ("public_id");
CREATE TABLE IF NOT EXISTS "users" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "public_id" VARCHAR(27) NOT NULL UNIQUE,
    "username" VARCHAR(100) NOT NULL UNIQUE,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "hashed_password" VARCHAR(255) NOT NULL,
    "role" VARCHAR(50) NOT NULL DEFAULT 'customer',
    "is_active" INT NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS "idx_users_public__1c65a4" ON "users" ("public_id");
CREATE INDEX IF NOT EXISTS "idx_users_usernam_266d85" ON "users" ("username");
CREATE INDEX IF NOT EXISTS "idx_users_email_133a6f" ON "users" ("email");
CREATE TABLE IF NOT EXISTS "orders" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "order_id" VARCHAR(50) NOT NULL UNIQUE /* Pattern: <year+0000> e.g. 20250001 */,
    "public_id" VARCHAR(27) NOT NULL UNIQUE,
    "contact_name" VARCHAR(255) NOT NULL,
    "contact_email" VARCHAR(255) NOT NULL,
    "delivery_address" TEXT NOT NULL,
    "status" VARCHAR(50) NOT NULL DEFAULT 'pending_payment',
    "user_id" INT REFERENCES "users" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_orders_public__32168a" ON "orders" ("public_id");
CREATE TABLE IF NOT EXISTS "order_events" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "public_id" VARCHAR(27) NOT NULL UNIQUE,
    "event_type" VARCHAR(100) NOT NULL,
    "data" JSON,
    "occurred_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "order_id" INT NOT NULL REFERENCES "orders" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_order_event_public__bc5421" ON "order_events" ("public_id");
CREATE TABLE IF NOT EXISTS "order_items" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "public_id" VARCHAR(27) NOT NULL UNIQUE,
    "quantity" INT NOT NULL,
    "price_at_purchase" REAL NOT NULL,
    "item_id" INT NOT NULL REFERENCES "inventory_items" ("id") ON DELETE RESTRICT,
    "order_id" INT NOT NULL REFERENCES "orders" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_order_items_order_i_c57a29" UNIQUE ("order_id", "item_id")
);
CREATE INDEX IF NOT EXISTS "idx_order_items_public__8b0420" ON "order_items" ("public_id");
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
