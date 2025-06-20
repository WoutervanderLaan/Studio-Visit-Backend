from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.core.session_manager import VisitDep, session_manager
from app.models.schemas import SessionReturn
from ..dependencies import get_current_user
from app.models.db import User
from app.core.config import get_settings


settings = get_settings()

router = APIRouter(
    prefix="/session",
    tags=["session"],
)


@router.get(
    path="/retrieve",
    description="Retrieve the active studio visit session.",
)
async def retrieve_session(
    visit: VisitDep,
) -> SessionReturn:
    return SessionReturn(visit_id=str(visit.session_id))


@router.get(
    path="/reset",
    response_class=JSONResponse,
    dependencies=[Depends(get_current_user)],
    description="Reset an active studio visit session and start a new one.",
)
async def reset_session(user: User = Depends(get_current_user)) -> SessionReturn:
    session = session_manager.reset_session(user)
    return SessionReturn(visit_id=str(session.session_id))
