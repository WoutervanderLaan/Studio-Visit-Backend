from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import select
from app.core.database import SessionDep
from app.models.db import Session, User, Message
from typing import List
from ..dependencies import get_current_user
import os, shutil
from app.core.config import get_settings
from pathlib import Path

settings = get_settings()

router = APIRouter(
    prefix="/history",
    tags=["history"],
)


@router.get(
    path="/",
    summary="Get user chat history",
    response_model=List[Message],
    response_description="A list of the latest chat messages for the authenticated user.",
)
async def get_chat_history(
    session: SessionDep,
    user: User = Depends(get_current_user),
    offset: int | None = Query(default=0, ge=0, description="offset history messages"),
):
    """
    Retrieve the latest 10 chat messages for the authenticated user with optional offset.

    - **session**: Database session dependency.
    - **user**: The currently authenticated user (injected via dependency).

    Returns a list of `Message` objects representing the user's chat history, ordered by insertion.
    """
    logs = session.exec(
        select(Message).where(Message.user_id == user.id).offset(offset).limit(10)
    ).all()

    return logs


@router.get(
    path="/image/{filename:path}",
    summary="Fetch uploaded image by filename",
    response_class=FileResponse,
    response_description="Returns the requested image file if it exists.",
)
async def get_uploaded_image(
    filename: str,
) -> FileResponse:

    uploads_dir = Path(settings.uploads_dir).resolve()
    requested_path = (uploads_dir / filename).resolve()

    if not str(requested_path).startswith(str(uploads_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename path")

    if not requested_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(str(requested_path), media_type="image/png")


@router.delete(
    path="/reset",
    summary="Reset user chat history, visits and uploaded images",
    response_class=JSONResponse,
    response_description="Confirmation message after deletion.",
)
async def reset_history(session: SessionDep, user: User = Depends(get_current_user)):
    uploads_dir = settings.uploads_dir
    user_uploads_dir = f"{uploads_dir}/{user.id}"

    try:
        if os.path.exists(user_uploads_dir):
            shutil.rmtree(user_uploads_dir)

        all_messages = session.exec(
            select(Message).where(Message.user_id == user.id)
        ).all()

        all_visits = session.exec(
            select(Session).where(Session.user_id == user.id)
        ).all()

        for message in all_messages:
            session.delete(message)  # workaround

        for visit in all_visits:
            session.delete(visit)  # workaround

        session.commit()

        return JSONResponse({"detail": "Successfully deleted chat history"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting data: {e}")
