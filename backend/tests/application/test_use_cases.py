import logging

import pytest

from app.application.dto.limits import InputLimits
from app.application.use_cases.generate_text import GenerateText
from app.application.use_cases.load_model import LoadModel
from app.application.use_cases.tokenize_prompt import TokenizePrompt
from app.domain.exceptions import (
    InferenceFailedError,
    InvalidGenerationConfigError,
    InvalidPromptError,
    ModelLoadError,
    ModelNotLoadedError,
)
from app.domain.inference.generation import GenerationConfig
from app.domain.models.model_spec import ModelSpec
from tests.fakes.fake_model_execution import FakeModelExecution

SPEC = ModelSpec("HuggingFaceTB/SmolLM2-360M-Instruct", "a10cc1512eabd3dde888204e902eca88bddb4951")
LIMITS = InputLimits(max_prompt_chars=4000, max_new_tokens=256)


def loaded_fake(**kwargs) -> FakeModelExecution:
    fake = FakeModelExecution(**kwargs)
    fake.load(SPEC)
    fake.calls.clear()
    return fake


def test_load_model_loads_port():
    fake = FakeModelExecution()
    LoadModel(fake).execute(SPEC)
    assert fake.is_loaded()


def test_load_failure_raises_and_stays_unloaded():
    fake = FakeModelExecution(fail_load=True)
    with pytest.raises(ModelLoadError):
        LoadModel(fake).execute(SPEC)
    assert not fake.is_loaded()


def test_retry_after_failed_load_succeeds():
    fake = FakeModelExecution(fail_load=True)
    use_case = LoadModel(fake)
    with pytest.raises(ModelLoadError):
        use_case.execute(SPEC)
    fake.fail_load = False
    use_case.execute(SPEC)
    assert fake.is_loaded()


@pytest.mark.parametrize("prompt", ["", "   \n", "x" * 4001])
def test_tokenize_rejects_invalid_prompt_without_calling_port(prompt):
    fake = loaded_fake()
    with pytest.raises(InvalidPromptError):
        TokenizePrompt(fake, LIMITS).execute(prompt)
    assert fake.calls == []


@pytest.mark.parametrize("prompt", ["", "   \n", "x" * 4001])
def test_generate_rejects_invalid_prompt_without_calling_port(prompt):
    fake = loaded_fake()
    with pytest.raises(InvalidPromptError):
        GenerateText(fake, LIMITS).execute(prompt, GenerationConfig())
    assert fake.calls == []


def test_generate_rejects_config_above_limit():
    fake = loaded_fake()
    with pytest.raises(InvalidGenerationConfigError):
        GenerateText(fake, LIMITS).execute("hello", GenerationConfig(max_new_tokens=257))
    assert fake.calls == []


def test_generate_returns_result_within_limit():
    fake = loaded_fake()
    result = GenerateText(fake, LIMITS).execute("hello world", GenerationConfig(max_new_tokens=8))
    assert 0 < result.output_tokens <= 8
    assert result.prompt_tokens == 2


def test_generate_before_load_raises_model_not_loaded():
    with pytest.raises(ModelNotLoadedError):
        GenerateText(FakeModelExecution(), LIMITS).execute("hello", GenerationConfig())


def test_tokenize_returns_count():
    result = TokenizePrompt(loaded_fake(), LIMITS).execute("a b c")
    assert result.count == 3


def test_use_cases_never_log_prompt(caplog):
    marker = "SECRET-PROMPT-123"
    caplog.set_level(logging.DEBUG)
    fake = loaded_fake()
    GenerateText(fake, LIMITS).execute(marker, GenerationConfig())
    TokenizePrompt(fake, LIMITS).execute(marker)
    failing = loaded_fake(fail_generate=True)
    with pytest.raises(InferenceFailedError):
        GenerateText(failing, LIMITS).execute(marker, GenerationConfig())
    with pytest.raises(InvalidPromptError):
        TokenizePrompt(fake, LIMITS).execute(" ")
    assert marker not in caplog.text
    for record in caplog.records:
        assert marker not in str(record.__dict__)
