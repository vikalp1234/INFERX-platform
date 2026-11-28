import json

import pytest
from fastapi.testclient import TestClient

from tests.adapters.http.helpers import make_test_app

MARKER = "SECRET-MARKER"


@pytest.fixture
def client():
    return TestClient(make_test_app(), raise_server_exceptions=False)


def assert_envelope(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id"}
    assert body["error"]["code"] == code
    assert body["error"]["request_id"] == response.headers["x-request-id"]


@pytest.mark.parametrize(
    ("kind", "status", "code"),
    [
        ("invalid_prompt", 422, "invalid_request"),
        ("invalid_config", 422, "invalid_request"),
        ("not_loaded", 409, "model_not_loaded"),
        ("overloaded", 429, "overloaded"),
        ("inference", 500, "inference_failed"),
        ("load", 500, "internal_error"),
    ],
)
def test_domain_errors_map_to_stable_envelope(client, kind, status, code):
    response = client.get(f"/raise/{kind}")
    assert_envelope(response, status, code)


def test_overloaded_has_retry_after(client):
    assert client.get("/raise/overloaded").headers["retry-after"] == "1"


def test_unexpected_error_is_internal_error_without_text(client):
    response = client.get("/boom")
    assert_envelope(response, 500, "internal_error")
    assert MARKER not in response.text


def test_validation_error_does_not_echo_input(client):
    response = client.post("/echo", json={"prompt": MARKER, "bogus": 1})
    assert_envelope(response, 422, "invalid_request")
    assert MARKER not in response.text
    assert "bogus" in response.json()["error"]["message"]


def test_malformed_json_does_not_echo_body(client):
    response = client.post(
        "/echo", content=f'{{"prompt": "{MARKER}", ', headers={"content-type": "application/json"}
    )
    assert_envelope(response, 422, "invalid_request")
    assert MARKER not in response.text


@pytest.mark.parametrize(
    "payload",
    [
        {"prompt": "hi", "temperature": -1},
        {"prompt": "hi", "top_k": "5"},
        {"prompt": "hi", "max_new_tokens": True},
        {"prompt": 5},
        {},
    ],
)
def test_bad_payloads_rejected_with_envelope(client, payload):
    assert_envelope(client.post("/echo", json=payload), 422, "invalid_request")


def test_greedy_with_top_k_rejected_by_domain_validation(client):
    response = client.post("/echo", json={"prompt": "hi", "top_k": 5})
    assert_envelope(response, 422, "invalid_request")


def test_valid_payload_accepted(client):
    body = {"prompt": "hi", "temperature": 0.8, "top_k": 5, "top_p": 0.9, "seed": 1}
    assert client.post("/echo", json=body).json() == {"ok": True}


def test_unknown_route_uses_envelope(client):
    assert_envelope(client.get("/nope"), 404, "not_found")
    assert_envelope(client.delete("/echo"), 405, "method_not_allowed")


def test_no_model_id_field_in_generate_schema():
    from app.adapters.inbound.http.schemas import GenerateRequest, TokenizeRequest

    for schema in (GenerateRequest, TokenizeRequest):
        assert not any("model" in name for name in schema.model_fields)
    assert json.dumps(GenerateRequest.model_json_schema()).count("additionalProperties") >= 1
