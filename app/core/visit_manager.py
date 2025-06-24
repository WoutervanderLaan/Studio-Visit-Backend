from typing import Annotated
from uuid import uuid4
from fastapi import Depends, HTTPException
from sqlmodel import select, update
from app.api.dependencies import get_current_user, get_ws_user
from app.core.database import SessionDep
from app.models.db import Session, User
from app.services.studio_visit import StudioVisit
from datetime import datetime


class VisitManager:
    """
    Manages Visits(sessions) for users.
    """

    def reset_visit(self, session: SessionDep, user: User) -> StudioVisit:
        if self._has_active_visit(session, user):
            self._finish_visit(session, user)

        return self._start_visit(session, user)

    def get_or_start_visit(
        self, session: SessionDep, user: User | None = Depends(get_current_user)
    ):
        if not user:
            raise HTTPException(401, "Not authorized")

        active_visit = self._get_visit(session, user)

        return active_visit if active_visit else self._start_visit(session, user)

    def _get_visit(
        self,
        session: SessionDep,
        user: User,
    ) -> StudioVisit | None:
        active_session = session.exec(
            select(Session).where(
                (Session.user_id == user.id) & (Session.finished_at == None)
            )
        ).first()

        if active_session:
            active_visit = StudioVisit(active_session.id, user)
            return active_visit

        return None

    def _start_visit(self, session: SessionDep, user: User) -> StudioVisit:
        visit_db = Session(
            user_id=user.id,
        )

        session.add(visit_db)
        session.commit()
        session.refresh(visit_db)

        new_visit = StudioVisit(session_id=visit_db.id, user=user)

        return new_visit

    def _has_active_visit(self, session: SessionDep, user: User) -> bool:
        return bool(self._get_visit(session, user))

    def _finish_visit(self, session: SessionDep, user: User) -> None:
        visit = session.exec(
            select(Session).where(
                (Session.user_id == user.id) & (Session.finished_at == None)
            )
        ).first()

        if not visit:
            raise HTTPException(500, "No active visit found.")

        visit.finished_at = datetime.now()
        session.add(visit)
        session.commit()
        session.refresh(visit)


visit_manager = VisitManager()


VisitDep = Annotated[StudioVisit, Depends(visit_manager.get_or_start_visit)]


async def get_ws_visit(session: SessionDep, user: User = Depends(get_ws_user)):
    return visit_manager.get_or_start_visit(session, user)
