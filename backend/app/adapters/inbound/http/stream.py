"""POST /v1/generate/stream: Server-Sent Events.

Validation, the model-loaded check and the capacity pre-check run before the response
starts, so those failures are ordinary JSON errors (422/409/429). After that the stream is
``token`` events and exactly one terminal ``done`` or ``error`` event. The client
disconnecting (or the task being cancelled) cancels generation and frees the slot.
"""

import asyncio
import threading
from collections.abc import AsyncIterator, Iterator
from typing import Any

import anyio
from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.adapters.inbound.http.dependencies import Deps
from app.adapters.inbound.http.errors import describe_error, envelope_body, request_id_of
from app.adapters.inbound.http.schemas import GenerateRequest
from app.adapters.inbound.http.sse import format_sse
from app.application.dto.metrics import RunMetrics
from app.domain.inference.streaming import StreamFinished, StreamItem, TokenDelta

stream_router = APIRouter(prefix="/v1")

_END = object()
_POLL_S = 0.1


def _next(iterator: Iterator[StreamItem]) -> Any:
    return next(iterator, _END)


@stream_router.post("/generate/stream")
async def generate_stream(body: GenerateRequest, request: Request, deps: Deps) -> StreamingResponse:
    config = body.to_config()
    cancel = threading.Event()
    request_id = request_id_of(request)
    items = deps.stream_generation.execute(body.prompt, config, cancel)

    def done_event(result: Any) -> bytes:
        try:
            kv = deps.estimate_kv_cache.execute(result.prompt_tokens + result.output_tokens)
        except Exception:
            kv = None
        return format_sse(
            "done",
            {
                "request_id": request_id,
                "finish_reason": str(result.finish_reason) if result.finish_reason else None,
                "prompt_tokens": result.prompt_tokens,
                "output_tokens": result.output_tokens,
                "metrics": RunMetrics.from_result(result, kv).to_dict(),
            },
        )

    async def events() -> AsyncIterator[bytes]:
        pending: asyncio.Future[Any] | None = None
        disconnected = False
        try:
            while True:
                pending = asyncio.ensure_future(run_in_threadpool(_next, items))
                while not pending.done():
                    await asyncio.wait({pending}, timeout=_POLL_S)
                    if not pending.done() and not disconnected and await request.is_disconnected():
                        disconnected = True
                        cancel.set()
                try:
                    item = pending.result()
                except Exception as exc:
                    _, code, message = describe_error(exc)
                    envelope = envelope_body(code, message, request_id)
                    yield format_sse("error", envelope)
                    return
                if disconnected or item is _END:
                    return
                if isinstance(item, TokenDelta):
                    yield format_sse("token", {"index": item.index, "text": item.text})
                elif isinstance(item, StreamFinished):
                    yield done_event(item.result)
                    return
        finally:
            cancel.set()
            with anyio.CancelScope(shield=True):
                if pending is not None and not pending.done():
                    await asyncio.wait({pending})
                await run_in_threadpool(items.close)  # type: ignore[attr-defined]

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(events(), media_type="text/event-stream", headers=headers)
