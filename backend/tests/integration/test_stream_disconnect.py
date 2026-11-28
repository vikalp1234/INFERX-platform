"""Real-uvicorn tests: a client that disconnects must stop generation and free its slot."""

import socket
import threading
import time
from contextlib import contextmanager

import httpx
import uvicorn

from app.bootstrap.app_factory import create_app
from app.bootstrap.container import build_container
from app.infrastructure.config.settings import Settings
from tests.fakes.fake_model_execution import FakeModelExecution

DEADLINE_S = 5.0


@contextmanager
def running_server(fake: FakeModelExecution, **settings):
    container = build_container(Settings(_env_file=None, **settings), fake)
    container.load_model.execute(container.settings.to_model_spec())
    config = uvicorn.Config(
        create_app(container), host="127.0.0.1", port=0, log_level="warning", lifespan="on"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started, "server did not start"
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}", container
    finally:
        server.should_exit = True
        thread.join(10)


def wait_for(predicate, timeout=DEADLINE_S):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def slow_fake() -> FakeModelExecution:
    return FakeModelExecution(delay_s=0.05, n_pieces=200)


def test_disconnect_mid_stream_cancels_and_frees_slot():
    fake = slow_fake()
    with running_server(fake) as (url, container):
        body = {"prompt": "hello", "max_new_tokens": 200}
        with httpx.stream("POST", f"{url}/v1/generate/stream", json=body, timeout=5) as response:
            first_event = next(line for line in response.iter_lines() if line.startswith("event:"))
            assert first_event == "event: token"
        assert wait_for(lambda: container.gate.running == 0), "slot was not freed"
        assert wait_for(lambda: fake.streams_closed == 1), "port stream was not closed"
        assert fake.deltas_sent < 200, "generation ran to completion after disconnect"
        follow_up = httpx.post(f"{url}/v1/generate", json={"prompt": "hi", "max_new_tokens": 3})
        assert follow_up.status_code == 200


def test_disconnect_without_reading_frees_slot():
    fake = slow_fake()
    with running_server(fake) as (url, container):
        host, port = url.removeprefix("http://").split(":")
        payload = b'{"prompt": "hello", "max_new_tokens": 200}'
        request = (
            b"POST /v1/generate/stream HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
            + f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n".encode()
            + payload
        )
        with socket.create_connection((host, int(port)), timeout=5) as sock:
            sock.sendall(request)
            assert wait_for(lambda: container.gate.running == 1), "stream never started"
        assert wait_for(lambda: container.gate.running == 0), "slot was not freed"
        follow_up = httpx.post(f"{url}/v1/generate", json={"prompt": "hi", "max_new_tokens": 3})
        assert follow_up.status_code == 200


def test_error_after_tokens_over_real_http_has_single_terminal_event():
    fake = FakeModelExecution(fail_after=2)
    with running_server(fake) as (url, container):
        response = httpx.post(
            f"{url}/v1/generate/stream", json={"prompt": "hello", "max_new_tokens": 3}, timeout=5
        )
        names = [
            line.removeprefix("event: ")
            for line in response.text.splitlines()
            if line.startswith("event: ")
        ]
        assert names == ["token", "token", "error"]
        assert wait_for(lambda: container.gate.running == 0)
