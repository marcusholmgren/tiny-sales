from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "orders" ADD "user_id" INT;
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
        ALTER TABLE "orders" ADD CONSTRAINT "fk_orders_users_411bb784" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE SET NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "orders" DROP FOREIGN KEY "fk_orders_users_411bb784";
        ALTER TABLE "orders" DROP COLUMN "user_id";
        DROP TABLE IF EXISTS "users";"""
