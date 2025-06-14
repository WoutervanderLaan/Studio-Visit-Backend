from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel
from uuid import UUID, uuid4
from datetime import datetime


class Message(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    content: str
    role: str
    timestamp: datetime = Field(default_factory=datetime.now)
    image_filename: Optional[str] = Field(default=None)

    user: Optional["User"] = Relationship(back_populates="messages")


class User(SQLModel, table=True):
    id: UUID = Field(primary_key=True, default_factory=uuid4)
    email: str = Field(index=True, unique=True)
    hashed_password: str = Field(nullable=False)
    role: str = Field(default="user")
    created_at: datetime = Field(default_factory=datetime.now)

    messages: List[Message] = Relationship(back_populates="user")
