from fastapi import WebSocket, WebSocketException, security, Depends, HTTPException
import jwt
from sqlmodel import select
from ..core.database import SessionDep
from app.models.db import User
from app.core.config import get_settings

settings = get_settings()


oauth2_scheme = security.OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    description="Use the token obtained from the login endpoint to access protected routes.",
)


def get_current_user(
    session: SessionDep, token: str = Depends(oauth2_scheme)
) -> User | None:
    """
    Decode the access token and return the user information.
    """
    try:
        payload = jwt.decode(
            token, key=settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str | None = payload.get("sub")

        if not username:
            raise HTTPException(
                status_code=401,
                detail="Invalid token",
            )

        result = session.exec(select(User).where(User.email == username))
        user = result.first()

        return user

    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=401,
            detail=e,
        )


def require_admin(user: User = Depends(get_current_user)) -> User | None:
    """
    Ensure the user has the 'admin' scope.
    """
    if user and user.role != "admin":
        raise HTTPException(
            status_code=401,
            detail="Insufficient permissions",
        )
    return user


async def get_ws_user(websocket: WebSocket, session: SessionDep) -> User | None:
    token = websocket.headers.get("sec-websocket-protocol")

    if not token:
        raise WebSocketException(code=1008, reason="404: Missing token")

    try:
        user = get_current_user(session, token)

        if not user:
            raise WebSocketException(code=1008, reason="404: No user found")

        return user
    except Exception as auth_err:
        raise WebSocketException(code=1008, reason=str(auth_err))
