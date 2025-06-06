from typing import Optional
from . import models

async def get_user_by_username(username: str) -> Optional[models.User]:
    user = await models.User.get_or_none(username=username)
    return user

async def get_user_by_email(email: str) -> Optional[models.User]:
    user = await models.User.get_or_none(email=email)
    return user

async def create_user(user_in: dict, hashed_password_val: str) -> models.User:
    new_user = await models.User.create(
        **user_in,
        hashed_password=hashed_password_val
    )
    return new_user
