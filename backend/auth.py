import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from . import models, schemas # Assuming models and schemas are in the same directory or accessible

# Configuration
# In a real app, load from environment variables or a config file
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt-!ChangeMe!") # TODO: Use a strong, environment-based secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Scheme
# tokenUrl should point to your token endpoint, e.g., "/auth/token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user(username: str) -> Optional[models.User]:
    """Fetches a user by username from the database."""
    user = await models.User.get_or_none(username=username)
    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> models.User:
    """
    Dependency to get the current user from a JWT token.
    Raises HTTPException if the token is invalid or the user is not found/inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except (JWTError, ValidationError) as e: # Catch JWT errors and Pydantic validation errors
        # logger.error(f"Token decode/validation error: {e}") # Consider logging the error
        raise credentials_exception

    user = await get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user

async def get_current_active_user(
    current_user: Annotated[models.User, Depends(get_current_user)]
) -> models.User:
    """
    Dependency to get the current active user.
    This mainly serves as an example if you just need an active logged-in user
    without specific role checks yet.
    """
    # get_current_user already checks for is_active
    return current_user

async def get_current_active_admin_user(
    current_user: Annotated[models.User, Depends(get_current_user)]
) -> models.User:
    """
    Dependency to get the current active user and ensure they are an admin.
    """
    if not current_user.is_active: # Though get_current_user should handle this
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user

# Example of how you might protect an endpoint for customers:
async def get_current_active_customer_user(
    current_user: Annotated[models.User, Depends(get_current_user)]
) -> models.User:
    """
    Dependency to get the current active user and ensure they are a customer.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    if current_user.role != "customer": # Assuming "customer" is a valid role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for this user role.",
        )
    return current_user
