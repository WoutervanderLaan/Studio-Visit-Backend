from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.core.database import SessionDep
from app.core.visit_manager import VisitDep, visit_manager
from app.models.schemas import SessionReturn
from ..dependencies import get_current_user
from app.models.db import User
from app.core.config import get_settings


settings = get_settings()

router = APIRouter(
    prefix="/visit",
    tags=["visit"],
)


@router.get(
    path="/retrieve",
    description="Retrieve the active studio visit session.",
)
async def retrieve_visit(visit: VisitDep) -> SessionReturn:
    return SessionReturn(visit_id=str(visit.session_id))


@router.get(
    path="/reset",
    response_class=JSONResponse,
    description="Reset an active studio visit session and start a new one.",
)
async def reset_visit(
    session: SessionDep, user: User = Depends(get_current_user)
) -> SessionReturn:
    try:
        visit = visit_manager.reset_visit(session, user)
        return SessionReturn(visit_id=str(visit.session_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset visit: {str(e)}")
