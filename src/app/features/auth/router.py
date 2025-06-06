"""API routes for user authentication, including token generation and user registration."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from . import schemas
from . import security as auth_security
from . import service as auth_service

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["Authentication"],
    prefix="/auth"
)

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    user = await auth_service.get_user_by_username(username=form_data.username)
    if not user or not auth_security.verify_password(form_data.password, user.hashed_password):
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

@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: schemas.UserCreate):
    existing_user_by_username = await auth_service.get_user_by_username(username=user_in.username)
    if existing_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    existing_user_by_email = await auth_service.get_user_by_email(email=user_in.email)
    if existing_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    hashed_password = auth_security.get_password_hash(user_in.password)
    user_data_dict = user_in.model_dump(exclude={"password"})
    try:
        new_user_model = await auth_service.create_user(
            user_in=user_data_dict,
            hashed_password_val=hashed_password
        )
        return schemas.UserResponse.model_validate(new_user_model)
    except Exception as e:
        logger.error(f"Register user failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user.",
        )
