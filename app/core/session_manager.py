from typing import Annotated, Dict
from uuid import uuid4, UUID
from fastapi import Depends, HTTPException
from app.api.dependencies import get_current_user, get_ws_user
from app.models.db import User
from app.services.studio_visit import StudioVisit


class SessionManager:
    """
    Manages Sessions for users.
    """

    def __init__(self) -> None:
        self._sessions: Dict[UUID, StudioVisit] = {}

    def reset_session(self, user: User) -> StudioVisit:

        if self._has_session(user):
            self._delete_session(user)

        return self._create_session(user)

    def _get_session(
        self, user: User | None = Depends(get_current_user)
    ) -> StudioVisit:
        """
        Returns active session or creates a new session based on user ID.
        """
        if not user:
            raise HTTPException(401, "Not authorized")

        active_session = next(
            (
                session
                for session in self._sessions.values()
                if session.user.id == user.id
            ),
            None,
        )

        return active_session if active_session else self._create_session(user)

    def _create_session(self, user: User) -> StudioVisit:
        session_id = uuid4()
        new_session = StudioVisit(session_id=session_id, user=user)

        self._sessions[new_session.session_id] = new_session
        return new_session

    def _has_session(self, user: User) -> bool:
        """
        Checks if there is a current session active, based on session ID or user ID.
        """
        return user.id in [session.user.id for session in self._sessions.values()]

    def _delete_session(self, user: User) -> None:
        """
        Deletes session if active based on user ID or session ID.
        """
        session = self._get_session(user)
        del self._sessions[session.session_id]


session_manager = SessionManager()


VisitDep = Annotated[StudioVisit, Depends(session_manager._get_session)]


async def _get_ws_session(user: User = Depends(get_ws_user)):
    return session_manager._get_session(user)


WSVisitDep = Annotated[StudioVisit, Depends(_get_ws_session)]
