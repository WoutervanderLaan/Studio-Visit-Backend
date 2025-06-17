from uuid import UUID
from agents import TResponseInputItem
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    UploadFile,
    File,
)
from sqlmodel import select, desc
from app.core.database import SessionDep
from app.models.db import User, Message
from app.core.socket_manager import SocketManager
from ..dependencies import get_current_user, get_ws_user
from app.utils.image import convert_to_png_and_save, image_to_base64
from app.services.critic import chat, draw
from app.models.schemas import DrawRequest, ImageReturn, Line
from app.core.config import get_settings
from typing import List

router = APIRouter(prefix="/chat", tags=["chat"])

socket_manager = SocketManager()
settings = get_settings()


def generate_input_items(
    session: SessionDep, user_id: UUID
) -> list[TResponseInputItem]:
    conversation_history = session.exec(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(desc(Message.timestamp))
    ).fetchmany(5)

    # TODO: add RAG to find relevance
    # TODO: add session management to understand when a drawing is new vs a continuation

    input_items: list[TResponseInputItem] = []

    for message in conversation_history.__reversed__():
        if message.role == "user" or message.role == "assistant":
            if message.image_filename != None:
                file_path = f"{settings.uploads_dir}/{message.image_filename}"
                b64_image = image_to_base64(file_path)

                input_items.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_image",
                                "detail": "auto",
                                "image_url": f"data:image/jpeg;base64,{b64_image}",
                            }
                        ],
                    }
                )

            input_items.append(
                {
                    "role": message.role,
                    "type": "message",
                    "content": message.content,
                }
            )

    return input_items


@router.post(
    path="/image-critique",
    response_model=ImageReturn,
    summary="Upload an image for critique",
    description="""
    Upload a PNG image for critique. The image will be processed and critiqued by the assistant.
    Returns the filename, file size, and the message id of the critique.
    """,
    responses={
        200: {"description": "Image uploaded and critiqued successfully"},
        400: {"description": "Invalid image file or file type"},
        401: {"description": "Unauthorized"},
    },
)
async def upload_png(
    session: SessionDep,
    user: User = Depends(get_current_user),
    file: UploadFile = File(..., description="PNG image file to upload"),
):
    """
    Accept a PNG file upload and store it on disk. Only image files are allowed.
    Will be thoroughly critiqued by a not so easily impressed art critic.

    - **file**: PNG image file to upload.
    - Returns: filename, file size, and message id.
    """

    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    websocket = socket_manager.get(str(user.id))

    if websocket is None:
        raise HTTPException(status_code=400, detail="No active websocket for user.")

    contents = await file.read()

    try:
        filename = convert_to_png_and_save(contents, user_id=str(user.id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    input_items = generate_input_items(session, user.id)

    b64_image = image_to_base64(f"{settings.uploads_dir}/{filename}")

    input_items.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "detail": "auto",
                    "image_url": f"data:image/jpeg;base64,{b64_image}",
                }
            ],
        },
    )

    full_critique = ""

    async for chunk in chat(input_items):
        await websocket.send_text(chunk)
        full_critique += chunk

    await websocket.send_text("[END]")

    message = Message(
        user_id=user.id,
        content=full_critique,
        role="assistant",
        image_filename=filename,
    )

    session.add(message)
    session.commit()
    session.refresh(message)

    return ImageReturn(
        filename=filename, size=len(contents), message_id=str(message.id)
    )


@router.post(path="/draw", response_model=List[Line])
async def continue_drawing(
    req: DrawRequest,
    session: SessionDep,
    user: User = Depends(get_current_user),
):

    new_lines = await draw(lines=req.lines)

    return new_lines


@router.websocket(
    path="/",
    name="Chat WebSocket",
)
async def handle_websocket(
    websocket: WebSocket, session: SessionDep, user: User = Depends(get_ws_user)
):
    """
    WebSocket endpoint for real-time chat.

    - Accepts a prompt from the user.
    - Streams the assistant's response in chunks.
    - Stores both user and assistant messages in the database.
    - Closes the connection on error.
    """
    is_closed = False

    try:
        token = websocket.headers.get("sec-websocket-protocol")
        await websocket.accept(subprotocol=token)

        socket_manager.add(str(user.id), websocket)

        while True:
            try:
                prompt = await websocket.receive_text()

                input_items = generate_input_items(session, user.id)

                input_items.append(
                    {"role": "user", "type": "message", "content": prompt}
                )

                full_response = ""

                async for chunk in chat(input_items):
                    await websocket.send_text(chunk)
                    full_response += chunk

                await websocket.send_text("[END]")

                user_message = Message(
                    user_id=user.id, content=prompt, role="user", user=user
                )

                assistant_message = Message(
                    user_id=user.id, content=full_response, role="assistant", user=user
                )

                session.add_all([user_message, assistant_message])
                session.commit()
                session.refresh(user_message)
                session.refresh(assistant_message)
            except Exception as inner_e:
                if not is_closed:
                    await websocket.close(code=1011, reason=f"Error: {inner_e}")
                    is_closed = True
                break
    except Exception as outer_e:
        if not is_closed:
            try:
                await websocket.close(code=1011, reason=f"Fatal Error: {outer_e}")
            except RuntimeError:
                pass
    finally:
        socket_manager.remove(str(user.id))
