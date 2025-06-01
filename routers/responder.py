from datetime import datetime
import uuid
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    Path,
)
from pydantic import BaseModel, Field
from enum import Enum

from slowapi import Limiter
from slowapi.util import get_remote_address
from .auth import oauth2_scheme
from studio.studio_model import StudioModel
from studio.studio_logger import StudioLogger
from studio.sql_db import SessionDep, DBLog

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


@router.websocket("/ws/respond/{model_type}")
async def handle_websocket(
    websocket: WebSocket,
    session: SessionDep,
    model_type: Model = Path(description="Model selection", examples=["1", "2"]),
):
    print("\n\n[WebSocket Connection Established]")
    print("MODEL:", model_type)
    await websocket.accept()

    prompt = await websocket.receive_text()
    if not prompt:
        await websocket.close(code=400, reason="No prompt provided.")

    full_response = ""

    async for token in model.get_response_async(prompt):
        await websocket.send_text(token)
        full_response += token

    logger.log_interaction(prompt, full_response)

    log = DBLog(
        id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        user_input=prompt,
        model_input=full_response,
    )

    session.add(log)
    session.commit()
    session.refresh(log)
    await websocket.close(code=1000, reason="Response complete.")
