import re
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_var

REQUEST_ID_HEADER = b"x-request-id"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _resolve_request_id(scope)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((REQUEST_ID_HEADER, request_id.encode()))
            await send(message)

        token = request_id_var.set(request_id)
        try:
            await self.app(scope, receive, send_with_header)
        finally:
            request_id_var.reset(token)


def _resolve_request_id(scope: Scope) -> str:
    for name, value in scope.get("headers", ()):
        if name == REQUEST_ID_HEADER:
            candidate = value.decode("latin-1", errors="replace")
            if _SAFE_REQUEST_ID.match(candidate):
                return candidate
            break
    return uuid.uuid4().hex
