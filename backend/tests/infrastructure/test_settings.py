import pytest
from pydantic import ValidationError

from app.domain.exceptions import InvalidModelSpecError
from app.infrastructure.config.settings import Settings

PINNED = "a10cc1512eabd3dde888204e902eca88bddb4951"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in (
        "INFERX_ENV",
        "INFERX_LOG_LEVEL",
        "INFERX_MODEL_ID",
        "INFERX_MODEL_REVISION",
        "INFERX_MAX_PROMPT_CHARS",
        "INFERX_MAX_NEW_TOKENS",
    ):
        monkeypatch.delenv(key, raising=False)


def test_settings_defaults_use_pinned_revision():
    settings = Settings(_env_file=None)
    assert settings.model_revision == PINNED
    assert settings.to_model_spec().model_id == "HuggingFaceTB/SmolLM2-360M-Instruct"
    assert settings.to_input_limits().max_prompt_chars == 4000


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("INFERX_MAX_NEW_TOKENS", "8")
    assert Settings(_env_file=None).to_input_limits().max_new_tokens == 8


def test_placeholder_revision_fails_at_to_model_spec(monkeypatch):
    monkeypatch.setenv("INFERX_MODEL_REVISION", "REPLACE_WITH_PINNED_REVISION")
    settings = Settings(_env_file=None)
    with pytest.raises(InvalidModelSpecError):
        settings.to_model_spec()


@pytest.mark.parametrize("name", ["INFERX_MAX_PROMPT_CHARS", "INFERX_MAX_NEW_TOKENS"])
@pytest.mark.parametrize("value", ["0", "-5"])
def test_non_positive_limits_rejected(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
