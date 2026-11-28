import io
import json
import logging
import re

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.observability.logging import configure_logging
from tests.adapters.http.helpers import make_test_app

HEX32 = re.compile(r"^[0-9a-f]{32}$")


@pytest.fixture
def client():
    return TestClient(make_test_app(), raise_server_exceptions=False)


def test_valid_incoming_id_is_echoed(client):
    response = client.get("/rid", headers={"X-Request-ID": "abc-123_X.y"})
    assert response.headers["x-request-id"] == "abc-123_X.y"
    assert response.json()["request_id"] == "abc-123_X.y"


def test_missing_id_is_generated(client):
    response = client.get("/rid")
    assert HEX32.match(response.headers["x-request-id"])


@pytest.mark.parametrize("bad", ["a b", "x" * 65, "", "id;drop", "café"])
def test_invalid_incoming_id_is_replaced(client, bad):
    try:
        response = client.get("/rid", headers={"X-Request-ID": bad})
    except Exception:  # header not encodable by the client library
        pytest.skip("client refuses to send this header")
    assert HEX32.match(response.headers["x-request-id"])
    assert response.headers["x-request-id"] != bad


def test_error_responses_carry_the_same_id_in_header_and_body(client):
    response = client.get("/raise/not_loaded", headers={"X-Request-ID": "req-1"})
    assert response.headers["x-request-id"] == "req-1"
    assert response.json()["error"]["request_id"] == "req-1"


def test_log_records_carry_request_id():
    stream = io.StringIO()
    configure_logging("INFO", stream)
    client = TestClient(make_test_app())
    response = client.get("/rid", headers={"X-Request-ID": "log-1"})
    lines = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
    record = next(line for line in lines if line["message"] == "inside_request")
    assert record["request_id"] == "log-1"
    assert response.status_code == 200
    logging.getLogger().handlers.clear()
