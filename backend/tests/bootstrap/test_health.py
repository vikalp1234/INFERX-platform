import pytest
from fastapi.testclient import TestClient

from app.bootstrap.app_factory import create_app
from app.bootstrap.container import build_container
from app.domain.exceptions import ModelLoadError
from app.infrastructure.config.settings import Settings
from tests.fakes.fake_model_execution import FakeModelExecution


def make_container(**kwargs):
    return build_container(Settings(_env_file=None), FakeModelExecution(**kwargs))


def test_health_returns_ok():
    client = TestClient(create_app(make_container()))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_stays_ok_after_failed_model_load():
    container = make_container(fail_load=True)
    client = TestClient(create_app(container))
    with pytest.raises(ModelLoadError):
        container.load_model.execute(container.settings.to_model_spec())
    assert client.get("/health").status_code == 200


def test_main_module_importable_without_ml_extra():
    from app.main import app

    assert app.title
