from fastapi.testclient import TestClient

from tests.adapters.http.helpers import make_test_app


def test_content_length_over_limit_is_413():
    client = TestClient(make_test_app(max_body_bytes=1024), raise_server_exceptions=False)
    response = client.post("/echo", json={"prompt": "x" * 5000})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert "x" * 50 not in response.text


def test_chunked_body_over_limit_is_413():
    client = TestClient(make_test_app(max_body_bytes=1024), raise_server_exceptions=False)

    def chunks():
        for _ in range(10):
            yield b'{"prompt": "' + b"x" * 400 + b'"}'

    response = client.post("/echo", content=chunks(), headers={"content-type": "application/json"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_body_under_limit_passes():
    client = TestClient(make_test_app(max_body_bytes=1024))
    assert client.post("/echo", json={"prompt": "hi"}).status_code == 200
