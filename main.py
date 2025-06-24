from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import auth, chat, history, visit
from app.core.database import db

app = FastAPI()

sql_db = db

origins = ["http://localhost:3000", "https://www.woutervanderlaan.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(history.router)
app.include_router(visit.router)
