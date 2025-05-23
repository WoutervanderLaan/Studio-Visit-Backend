from fastapi import APIRouter, Query, Depends
from datetime import datetime
import json, os
from pydantic import BaseModel
from sqlmodel import select
from .auth import oauth2_scheme
from ..studio.sql_db import SessionDep, DBLog

router = APIRouter(
    prefix="/history", tags=["history"], responses={404: {"description": "Not found"}}
)

LOGS_PATH = "./logs/json"


class Log(BaseModel):
    id: str
    user: str
    assistant: str
    timestamp: str


class Logs(BaseModel):
    data: list[Log]


@router.get("/")
async def get_history(
    date: str = Query(
        default=datetime.now().strftime("%d-%m-%Y"),
        description="Retrieve chat history of specific date",
    ),
    token=Depends(oauth2_scheme),
) -> Logs:
    file_path = f"{LOGS_PATH}/{date}.json"

    if not os.path.exists(file_path):
        return Logs(data=[])

    with open(file_path, "r") as file:
        raw_data = json.load(file)
        data = [Log(**entry) for entry in raw_data]
        return Logs(data=data)


@router.get("/db")
async def get_history_db(
    session: SessionDep,
    token=Depends(oauth2_scheme),
):
    logs = session.exec(select(DBLog).offset(0).limit(100)).all()
    return logs
