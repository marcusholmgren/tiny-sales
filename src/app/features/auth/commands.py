"""Command objects and command handlers for authentication operations."""

import logging
from dataclasses import dataclass

from fastapi import HTTPException, status

from ...common import BaseCommand, CommandHandler
from . import schemas
from . import security as auth_security
from . import service as auth_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LoginCommand(BaseCommand):
    """Command payload for user login authentication."""

    username: str
    password: str


class LoginCommandHandler(CommandHandler[LoginCommand, dict]):
    """Command handler for authenticating a user and returning a JWT access token."""

    async def execute(self, command: LoginCommand) -> dict:
        """Executes the login operation.

        Args:
            command: The LoginCommand containing credentials.

        Returns:
            dict: Token dictionary with access_token and token_type.

        Raises:
            HTTPException: If authentication fails or user is inactive.
        """
        user = await auth_service.get_user_by_username(username=command.username)
        if not user or not auth_security.verify_password(
            command.password, user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )
        access_token = auth_security.create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}


@dataclass(frozen=True, slots=True)
class RegisterUserCommand(BaseCommand):
    """Command payload for user registration."""

    user_in: schemas.UserCreate


class RegisterUserCommandHandler(
    CommandHandler[RegisterUserCommand, schemas.UserResponse]
):
    """Command handler for registering new users."""

    async def execute(self, command: RegisterUserCommand) -> schemas.UserResponse:
        """Executes the user registration operation.

        Args:
            command: The RegisterUserCommand containing user creation schema.

        Returns:
            UserResponse: The registered user response schema.

        Raises:
            HTTPException: If username or email is already registered or creation fails.
        """
        user_in = command.user_in
        existing_user_by_username = await auth_service.get_user_by_username(
            username=user_in.username
        )
        if existing_user_by_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )
        existing_user_by_email = await auth_service.get_user_by_email(
            email=user_in.email
        )
        if existing_user_by_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        hashed_password = auth_security.get_password_hash(user_in.password)
        user_data_dict = user_in.model_dump(exclude={"password"})
        try:
            new_user_model = await auth_service.create_user(
                user_in=user_data_dict, hashed_password_val=hashed_password
            )
            return schemas.UserResponse.model_validate(new_user_model)
        except Exception as e:
            logger.exception("Register user failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create user.",
            )
