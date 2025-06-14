from fastapi import WebSocket


class SocketManager:
    """
    Manages WebSocket connections for users.
    """

    def __init__(self):
        self._sockets: dict[str, WebSocket] = {}

    def add(self, user_id: str, websocket: WebSocket):
        self._sockets[user_id] = websocket

    def remove(self, user_id: str):
        self._sockets.pop(user_id, None)

    def get(self, user_id: str) -> WebSocket | None:
        return self._sockets.get(user_id)

    def has(self, user_id: str) -> bool:
        return user_id in self._sockets
