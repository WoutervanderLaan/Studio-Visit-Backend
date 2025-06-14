from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine


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
