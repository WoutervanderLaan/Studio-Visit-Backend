from datetime import datetime
import uuid
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
)
from pydantic import BaseModel, Field
from enum import Enum

from slowapi import Limiter
from slowapi.util import get_remote_address
from .auth import oauth2_scheme
from studio.studio_model import StudioModel
from studio.studio_logger import StudioLogger
from studio.database import SessionDep, Message, User
from .auth import get_current_user

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/responder", tags=["responder"])
model = StudioModel()
logger = StudioLogger()


class Model(str, Enum):
    DEFAULT = "1"
    OPENAI = "2"


class PromptRequest(BaseModel):
    prompt: str = Field(examples=["Are ghosts real?"])
    model_type: Model | None = Field(
        description="Model selection", examples=["1", "2"], default=Model.DEFAULT
    )


class PromptReturn(BaseModel):
    response: str = Field(
        description="Response text from the model", examples=["Yes, ghosts are real."]
    )


@router.post("/respond")
@limiter.limit("5/minute")
async def studio_response(
    request: Request,
    response: Response,
    body: PromptRequest,
    token: str = Depends(oauth2_scheme),
) -> PromptReturn:
    """
    Generate a response from the model based on the provided prompt.
    """
    prompt = body.prompt
    model_type = body.model_type

    try:
        response_text = model.get_response(prompt)
        logger.log_interaction(prompt, response_text)

        return PromptReturn(response=response_text)

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Error generating response: {error}"
        )


async def get_ws_user(websocket: WebSocket, session: SessionDep):
    token = websocket.headers.get("sec-websocket-protocol")

    if not token:
        await websocket.accept()
        await websocket.close(code=1008, reason="404: Missing token")
        return

    try:
        return get_current_user(session, token)
    except Exception as auth_err:
        await websocket.accept(subprotocol=token)
        await websocket.close(code=1008, reason=str(auth_err))
        return


@router.websocket("/ws/respond")
async def handle_websocket(
    websocket: WebSocket, session: SessionDep, user: User = Depends(get_ws_user)
):
    is_closed = False

    try:
        token = websocket.headers.get("sec-websocket-protocol")
        await websocket.accept(subprotocol=token)

        while True:
            try:
                prompt = await websocket.receive_text()

                full_response = ""

                async for token_chunk in model.get_response_async(prompt):
                    await websocket.send_text(token_chunk)
                    full_response += token_chunk

                await websocket.send_text("[END]")

                logger.log_interaction(prompt, full_response)

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
                print("inner_e", inner_e)
                if not is_closed:
                    await websocket.close(code=1011, reason=f"Error: {inner_e}")
                    is_closed = True
                break
    except Exception as outer_e:
        print("outer_e", outer_e)
        if not is_closed:
            try:
                await websocket.close(code=1011, reason=f"Fatal Error: {outer_e}")
            except RuntimeError:
                pass
