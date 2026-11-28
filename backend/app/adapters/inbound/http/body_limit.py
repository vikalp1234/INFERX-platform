"""Reject oversized request bodies (declared or streamed) with a 413."""

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.adapters.inbound.http.errors import error_response
from app.adapters.inbound.http.request_id import new_request_id


class BodyTooLargeError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=413, detail="payload too large")


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > self.max_bytes:
            request_id = scope.get("state", {}).get("request_id") or new_request_id()
            response = error_response(413, "payload_too_large", "payload too large", request_id)
            await response(scope, receive, send)
            return
        total = 0

        async def limited_receive() -> Message:
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    raise BodyTooLargeError
            return message

        await self.app(scope, limited_receive, send)
