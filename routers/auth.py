from fastapi import APIRouter, Form, Response, Request, security, Depends, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta, timezone
import jwt, dotenv, os

from sqlmodel import select
from studio.database import SessionDep, User


router = APIRouter(
    prefix="/auth", tags=["auth"], responses={404: {"description": "Not found"}}
)

dotenv.load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 1

if not SECRET_KEY or not REFRESH_SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY and REFRESH_SECRET_KEY must be set in the environment"
    )


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
    scopes: str | None = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = security.OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    description="Use the token obtained from the login endpoint to access protected routes.",
    # scopes={
    #     "admin": "Admin access",
    #     "user": "User access",
    # },
)


def get_current_user(
    session: SessionDep, token: str = Depends(oauth2_scheme)
) -> User | None:
    """
    Decode the access token and return the user information.
    """
    try:
        payload = jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")

        if not username:
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
            )

        result = session.exec(select(User).where(User.email == username))

        return result.first()

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )


def require_admin(user: User = Depends(get_current_user)):
    """
    Ensure the user has the 'admin' scope.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=401,
            detail="Insufficient permissions",
        )


@router.post(
    "/register",
    dependencies=[
        Depends(require_admin),
    ],
    tags=["admin"],
)
async def register_user(
    session: SessionDep,
    username: EmailStr = Form(description="Email address", example="test@example.com"),
    password: str = Form(description="Strong password", example="Password123"),
):
    """
    Register a new user with the given username and password."""

    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters long")
    if not any(char.isdigit() for char in password):
        raise HTTPException(400, "Password must contain at least one number")
    if not any(char.isupper() for char in password):
        raise HTTPException(400, "Password must contain at least one uppercase letter")
    if not any(char.islower() for char in password):
        raise HTTPException(400, "Password must contain at least one lowercase letter")

    statement = select(User).where(User.email == username)

    result = session.exec(statement)
    user_in_db = result.first()

    if user_in_db:
        raise HTTPException(400, "User already exists")

    user = User(
        email=username,
        hashed_password=pwd_context.hash(password),
        role="admin",
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return {"message": f"User {username} registered successfully"}


@router.post("/login")
async def login_user(
    session: SessionDep,
    response: Response,
    form_data: security.OAuth2PasswordRequestForm = Depends(),
) -> dict[str, str]:
    """
    Login user and return access and refresh tokens.
    """

    statement = select(User).where(User.email == form_data.username)

    user = session.exec(statement).first()

    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = jwt.encode(
        payload={
            "sub": user.email,
            "role": user.role,
            "exp": datetime.now(timezone.utc) + access_token_expires,
        },
        key=SECRET_KEY,
        algorithm=ALGORITHM,
    )

    refresh_token = jwt.encode(
        payload={
            "sub": user.email,
            "role": user.role,
            "exp": datetime.now(timezone.utc) + refresh_token_expires,
        },
        key=REFRESH_SECRET_KEY,
        algorithm=ALGORITHM,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=60 * 60 * 24 * REFRESH_TOKEN_EXPIRE_DAYS,
        path="/",
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/refresh")
async def refresh_token(request: Request, session: SessionDep):
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(401, "Missing refresh token")

    try:
        payload: dict = jwt.decode(
            jwt=refresh_token, key=REFRESH_SECRET_KEY, algorithms=[ALGORITHM]
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
                + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            },
            key=SECRET_KEY,
            algorithm=ALGORITHM,
        )

        return Token(access_token=new_access_token, token_type="bearer")

    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid refresh token")


@router.delete("/logout")
async def logout_user(response: Response):
    """
    Log out user.
    """
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "User logged out successfully"}
