"""API routes for user authentication, using command handlers."""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from . import schemas
from .commands import (
    LoginCommand,
    LoginCommandHandler,
    RegisterUserCommand,
    RegisterUserCommandHandler,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Authentication"], prefix="/auth")


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    handler: Annotated[LoginCommandHandler, Depends()],
):
    """Authenticates a user and returns an access token."""
    command = LoginCommand(form_data=form_data)
    return await handler.execute(command)


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_in: schemas.UserCreate,
    handler: Annotated[RegisterUserCommandHandler, Depends()],
):
    """Registers a new user."""
    command = RegisterUserCommand(user_in=user_in)
    return await handler.execute(command)
