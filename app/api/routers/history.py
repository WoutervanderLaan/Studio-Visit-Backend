from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import select
from app.core.database import SessionDep
from app.models.db import User, Message
from typing import List
from ..dependencies import get_current_user
import os, shutil
from app.core.config import get_settings

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
):
    """
    Retrieve the latest 100 chat messages for the authenticated user.

    - **session**: Database session dependency.
    - **user**: The currently authenticated user (injected via dependency).

    Returns a list of `Message` objects representing the user's chat history, ordered by insertion.
    """
    logs = session.exec(
        select(Message).where(Message.user_id == user.id).offset(0).limit(100)
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
    """
    Fetch a stored image file by filename (image hash).

    - **filename**: The name (hash) of the image file to retrieve.

    Returns the image as a PNG file if it exists in the `uploads` directory.
    Raises a 404 error if the file is not found.
    """
    if "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = os.path.join(settings.uploads_dir, filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path, media_type="image/png")


@router.delete(
    path="/reset",
    summary="Reset user chat history and uploaded images",
    response_class=JSONResponse,
    response_description="Confirmation message after deletion.",
)
async def reset_history(session: SessionDep, user: User = Depends(get_current_user)):
    """
    Reset (delete) all chat history and uploaded images for the authenticated user.

    - **session**: Database session dependency.
    - **user**: The currently authenticated user (injected via dependency).

    This endpoint will:
    - Delete all image files in the user's upload directory (`uploads/{user.id}`).
    - Remove the user's upload directory if empty.
    - Delete all chat messages associated with the user from the database.

    Returns a success message if deletion is successful, or an error message if something goes wrong.
    """
    uploads_dir = settings.uploads_dir
    user_uploads_dir = f"{uploads_dir}/{user.id}"

    try:
        if os.path.exists(user_uploads_dir):
            shutil.rmtree(user_uploads_dir)

        all_messages = session.exec(
            select(Message).where(Message.user_id == user.id)
        ).all()

        for message in all_messages:
            session.delete(message)  # workaround

        session.commit()

        return JSONResponse({"detail": "Successfully deleted chat history"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting data: {e}")
