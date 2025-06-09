from fastapi import APIRouter, Depends
from sqlmodel import select
from studio.database import SessionDep, Message, User
from typing import List
from .auth import get_current_user


router = APIRouter(
    prefix="/history", tags=["history"], responses={404: {"description": "Not found"}}
)


@router.get("/", response_model=List[Message])
async def get_history_db(
    session: SessionDep,
    user: User = Depends(get_current_user),
):
    logs = session.exec(
        select(Message).where(Message.user_id == user.id).offset(0).limit(100)
    ).all()

    return logs
