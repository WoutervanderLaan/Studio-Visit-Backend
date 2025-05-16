from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, transcribe, responder, history
from slowapi import Limiter
from slowapi.util import get_remote_address
from .studio.sql_db import db


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     sql_db = await db


app = FastAPI()
aql_db = db
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
##TODO: limiter

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transcribe.router)
app.include_router(responder.router)
app.include_router(history.router)
