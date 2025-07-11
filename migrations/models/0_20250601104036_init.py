from tortoise import BaseDBAsyncClient


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
