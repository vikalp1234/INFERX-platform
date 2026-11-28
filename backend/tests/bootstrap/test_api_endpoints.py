import threading

import pytest
from fastapi.testclient import TestClient

from app.bootstrap.app_factory import create_app
from app.bootstrap.container import build_container
from app.infrastructure.config.settings import Settings
from tests.fakes.fake_model_execution import FakeModelExecution

MARKER = "PROMPT-MARKER-xyz"


def make_client(fake=None, loaded=True, **settings):
    fake = fake or FakeModelExecution()
    container = build_container(Settings(_env_file=None, **settings), fake)
    if loaded:
        container.load_model.execute(container.settings.to_model_spec())
    return TestClient(create_app(container), raise_server_exceptions=False), fake, container


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_model_status_loaded_and_unloaded():
    client, _, container = make_client(loaded=False)
    body = client.get("/v1/model").json()
    assert body["loaded"] is False
    assert body["model_id"] == container.settings.model_id
    container.load_model.execute(container.settings.to_model_spec())
    assert client.get("/v1/model").json()["loaded"] is True


def test_tokenize_returns_counts_and_ids():
    client, _, _ = make_client()
    response = client.post("/v1/tokenize", json={"prompt": "hello brave new world"})
    body = response.json()
    assert response.status_code == 200
    assert body["token_count"] == 4
    assert len(body["token_ids"]) == 4
    assert body["request_id"] == response.headers["x-request-id"]


def test_generate_happy_path_returns_labelled_metrics():
    client, _, _ = make_client()
    response = client.post("/v1/generate", json={"prompt": "hello", "max_new_tokens": 3})
    body = response.json()
    assert response.status_code == 200
    assert body["text"] == "fake output text"
    assert body["finish_reason"] == "length"
    assert body["output_tokens"] == 3
    assert body["metrics"]["ttft_ms"]["provenance"] == "measured"
    assert body["metrics"]["kv_cache_bytes_estimate"]["provenance"] == "derived_from_model_config"
    assert body["request_id"] == response.headers["x-request-id"]


def test_sampling_fields_reach_the_port():
    client, fake, _ = make_client()
    client.post(
        "/v1/generate",
        json={"prompt": "hi", "temperature": 0.8, "top_k": 5, "top_p": 0.9, "seed": 3},
    )
    cfg = fake.configs[-1]
    assert (cfg.temperature, cfg.top_k, cfg.top_p, cfg.seed) == (0.8, 5, 0.9, 3)


@pytest.mark.parametrize("path", ["/v1/tokenize", "/v1/generate"])
def test_unloaded_model_is_409_on_post_routes(path):
    client, _, _ = make_client(loaded=False)
    assert_error(client.post(path, json={"prompt": "hi"}), 409, "model_not_loaded")
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"prompt": "hi", "max_new_tokens": 9999},
        {"prompt": "   "},
        {"prompt": ""},
        {"prompt": "x" * 5000},
    ],
)
def test_limits_and_empty_prompt_are_422(payload):
    client, _, _ = make_client()
    response = client.post("/v1/generate", json=payload)
    assert_error(response, 422, "invalid_request")
    assert "x" * 50 not in response.text


def test_inference_failure_is_500_without_prompt_text():
    client, _, _ = make_client(FakeModelExecution(fail_generate=True))
    response = client.post("/v1/generate", json={"prompt": MARKER})
    assert_error(response, 500, "inference_failed")
    assert MARKER not in response.text


class BlockingFake(FakeModelExecution):
    def __init__(self) -> None:
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()

    def generate(self, prompt, config):
        self.entered.set()
        self.release.wait(5)
        return super().generate(prompt, config)


def test_overload_returns_429_with_retry_after_when_busy_and_no_waiting_room():
    fake = BlockingFake()
    client, _, _ = make_client(fake, max_concurrent_requests=1, max_waiting_requests=0)
    first = threading.Thread(
        target=lambda: client.post("/v1/generate", json={"prompt": "a"}), daemon=True
    )
    first.start()
    assert fake.entered.wait(2)
    response = client.post("/v1/generate", json={"prompt": "b"})
    assert_error(response, 429, "overloaded")
    assert response.headers["retry-after"] == "1"
    fake.release.set()
    first.join(5)
    assert client.post("/v1/generate", json={"prompt": "c"}).status_code == 200


def test_autoload_enabled_loads_model_at_startup():
    container = build_container(Settings(_env_file=None, autoload_model=True), FakeModelExecution())
    with TestClient(create_app(container)) as client:
        assert client.get("/v1/model").json()["loaded"] is True


def test_autoload_disabled_does_not_load():
    container = build_container(Settings(_env_file=None), FakeModelExecution())
    with TestClient(create_app(container)) as client:
        assert client.get("/v1/model").json()["loaded"] is False


def test_autoload_failure_keeps_serving_health_and_409():
    container = build_container(
        Settings(_env_file=None, autoload_model=True), FakeModelExecution(fail_load=True)
    )
    with TestClient(create_app(container), raise_server_exceptions=False) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert_error(client.post("/v1/generate", json={"prompt": "hi"}), 409, "model_not_loaded")
