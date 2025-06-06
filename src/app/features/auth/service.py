"""Business logic for authentication, such as user creation and retrieval."""
from typing import Optional
from . import models

async def get_user_by_username(username: str) -> Optional[models.User]:
    """Retrieves a user by their username.

    Args:
        username: The username of the user to retrieve.

    Returns:
        The User object if found, otherwise None.
    """
    user = await models.User.get_or_none(username=username)
    return user

async def get_user_by_email(email: str) -> Optional[models.User]:
    """Retrieves a user by their email address.

    Args:
        email: The email address of the user to retrieve.

    Returns:
        The User object if found, otherwise None.
    """
    user = await models.User.get_or_none(email=email)
    return user

async def create_user(user_in: dict, hashed_password_val: str) -> models.User:
    """Creates a new user in the database.

    Args:
        user_in: A dictionary containing the user data (excluding password).
        hashed_password_val: The hashed password for the new user.

    Returns:
        The newly created User object.
    """
    new_user = await models.User.create(
        **user_in,
        hashed_password=hashed_password_val
    )
    return new_user
