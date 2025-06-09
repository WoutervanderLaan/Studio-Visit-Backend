from typing import Annotated, List, Optional
from fastapi import Depends
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine
from uuid import UUID, uuid4
from datetime import datetime


class Message(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    content: str
    role: str
    timestamp: datetime = Field(default_factory=datetime.now)
    # reply_to_message_id: Optional[UUID] = Field(default=None, foreign_key="message.id")
    # session_id: Optional[UUID] = None

    user: Optional["User"] = Relationship(back_populates="messages")
    # reply_to: Optional["Message"] = Relationship(
    #     sa_relationship_kwargs={"remote_side": "Message.id"}
    # )
    # replies: List["Message"] = Relationship(back_populates="reply_to")


class User(SQLModel, table=True):
    id: UUID = Field(primary_key=True, default_factory=uuid4)
    email: str = Field(index=True, unique=True)
    hashed_password: str = Field(nullable=False)
    role: str = Field(default="user")
    created_at: datetime = Field(default_factory=datetime.now)

    messages: List[Message] = Relationship(back_populates="user")


# class UserCreate(SQLModel):
#     email: EmailStr
#     hashed_password: str
#     role: Optional[List[str]] = ["user"]


# class MessageCreate(SQLModel):
#     user_id: UUID
#     content: str
#     role: str  # 'user' or 'assistant'
#     reply_to_message_id: Optional[UUID] = None


# class MessageOut(SQLModel):
#     id: UUID
#     user_id: UUID
#     role: str
#     content: str
#     timestamp: datetime
#     reply_to_message_id: Optional[UUID]


class Database:
    def __init__(self, sqlite_file_name="database.db"):
        self._sqlite_url = f"sqlite:///{sqlite_file_name}"

        connect_args = {"check_same_thread": False}

        self._engine = create_engine(self._sqlite_url, connect_args=connect_args)

        self._create_db_and_tables()

    def _create_db_and_tables(self):
        SQLModel.metadata.create_all(self._engine)

    def get_session(self):
        with Session(self._engine) as session:
            yield session


db = Database()

SessionDep = Annotated[Session, Depends(db.get_session)]
