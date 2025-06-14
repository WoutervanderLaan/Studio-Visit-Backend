from fastapi import APIRouter, Form, Response, Request, security, Depends, HTTPException
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from pydantic import EmailStr
from datetime import datetime, timedelta, timezone
import jwt
from ..dependencies import require_admin
from sqlmodel import select
from app.core.database import SessionDep
from app.models.schemas import Token
from app.models.db import User
from app.core.config import get_settings


settings = get_settings()

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"},
    },
)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post(
    path="/register",
    dependencies=[
        Depends(require_admin),
    ],
    summary="Register a new user",
    description="""
    Register a new user with an email and password. Only accessible to admin users.

    Password requirements:
    - At least 8 characters
    - At least one number
    - At least one uppercase letter
    - At least one lowercase letter
    """,
    response_class=JSONResponse,
    response_description="Returns a success message upon successful registration.",
    tags=["admin"],
    responses={
        201: {"description": "User registered successfully"},
        400: {"description": "Validation error or user already exists"},
        401: {"description": "Unauthorized"},
    },
)
async def register_user(
    session: SessionDep,
    username: EmailStr = Form(
        ...,
        description="Email address of the new user",
        example="test@example.com",
    ),
    password: str = Form(
        ...,
        description="Strong password for the new user",
        example="Password123",
        min_length=8,
    ),
):
    """
    Register a new user with the given username (email) and password.

    - **username**: Email address of the user.
    - **password**: Password (must meet requirements).
    """

    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters long")
    if not any(char.isdigit() for char in password):
        raise HTTPException(400, "Password must contain at least one number")
    if not any(char.isupper() for char in password):
        raise HTTPException(400, "Password must contain at least one uppercase letter")
    if not any(char.islower() for char in password):
        raise HTTPException(400, "Password must contain at least one lowercase letter")

    result = session.exec(select(User).where(User.email == username.lower()))
    user_in_db = result.first()

    if user_in_db:
        raise HTTPException(400, "User already exists")

    user = User(
        email=username.lower(),
        hashed_password=pwd_context.hash(password),
        role="user",
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return JSONResponse({"detail": f"User {username} registered successfully"}, 201)


@router.post(
    path="/login",
    summary="Log in to the app",
    description="""
    Authenticate a user and return an access token and a refresh token (as a secure cookie).

    - Returns a JWT access token for API authentication.
    - Sets a refresh token as an HTTP-only cookie for session renewal.
    """,
    response_model=Token,
    response_description="Returns access token and token type.",
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {"description": "Invalid credentials"},
    },
)
async def login_user(
    session: SessionDep,
    response: Response,
    form_data: security.OAuth2PasswordRequestForm = Depends(
        security.OAuth2PasswordRequestForm
    ),
):
    """
    Log in a user and return access and refresh tokens.

    - **username**: User's email address.
    - **password**: User's password.
    - Sets a secure, HTTP-only refresh token cookie.
    """

    statement = select(User).where(User.email == form_data.username)

    user = session.exec(statement).first()

    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)

    access_token = jwt.encode(
        payload={
            "sub": user.email,
            "role": user.role,
            "exp": datetime.now(timezone.utc) + access_token_expires,
        },
        key=settings.secret_key,
        algorithm=settings.algorithm,
    )

    refresh_token = jwt.encode(
        payload={
            "sub": user.email,
            "role": user.role,
            "exp": datetime.now(timezone.utc) + refresh_token_expires,
        },
        key=settings.refresh_secret_key,
        algorithm=settings.algorithm,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=60 * 60 * 24 * settings.refresh_token_expire_days,
        path="/",
    )

    return Token(access_token=access_token, token_type="bearer")


@router.get(
    path="/refresh",
    summary="Refresh access token",
    description="""
    Obtain a new access token using a valid refresh token (sent as a cookie).

    - Requires a valid refresh token cookie.
    - Returns a new JWT access token.
    """,
    response_model=Token,
    response_description="Returns new access token and token type.",
    responses={
        200: {"description": "New access token issued"},
        401: {"description": "Missing, expired, or invalid refresh token"},
    },
)
async def refresh_token(
    request: Request,
    response: Response,
    session: SessionDep,
):
    """
    Refresh the access token using the refresh token cookie.

    - Requires a valid refresh token in the cookie.
    - Returns a new access token.
    """

    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(401, "Missing refresh token")

    try:
        payload: dict = jwt.decode(
            jwt=refresh_token,
            key=settings.refresh_secret_key,
            algorithms=[settings.algorithm],
        )

        username: str = payload.get("sub", "")
        statement = select(User).where(User.email == username)

        result = session.exec(statement)
        user_in_db = result.first()

        if not username or not user_in_db:
            raise HTTPException(401, "Invalid user")

        new_access_token = jwt.encode(
            payload={
                "sub": username,
                "role": user_in_db.role,
                "exp": datetime.now(timezone.utc)
                + timedelta(minutes=settings.access_token_expire_minutes),
            },
            key=settings.secret_key,
            algorithm=settings.algorithm,
        )

        return Token(access_token=new_access_token, token_type="bearer")
    except jwt.ExpiredSignatureError:
        response.delete_cookie(key="refresh_token", path="/")
        raise HTTPException(401, "Expired refresh token")
    except jwt.PyJWTError:
        response.delete_cookie(key="refresh_token", path="/")
        raise HTTPException(401, "Invalid refresh token")


@router.delete(
    path="/logout",
    summary="Log out the user",
    description="""
    Log out the current user by deleting the refresh token cookie.

    - Removes the refresh token from the browser.
    - User must log in again to obtain new tokens.
    """,
    response_class=JSONResponse,
    response_description="Successful logout message.",
    responses={
        200: {"description": "User logged out successfully"},
    },
)
async def logout_user(response: Response):
    """
    Log out the current user by deleting the refresh token cookie.

    - Removes the refresh token from the browser.
    """

    response.delete_cookie(key="refresh_token", path="/")
    return JSONResponse({"detail": "User logged out successfully"})
