"""Pure ASGI middleware: assign, validate and echo a request ID."""

import re
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.application.request_context import request_id_var

_VALID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
HEADER = b"x-request-id"


def new_request_id() -> str:
    return uuid.uuid4().hex


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope["headers"]).get(HEADER, b"").decode("latin-1")
        request_id = incoming if _VALID.match(incoming) else new_request_id()
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_var.set(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [h for h in message.get("headers", []) if h[0].lower() != HEADER]
                headers.append((HEADER, request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)
