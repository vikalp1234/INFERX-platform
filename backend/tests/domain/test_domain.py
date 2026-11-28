import pytest

from app.domain.exceptions import (
    InferenceFailedError,
    InferxError,
    InvalidGenerationConfigError,
    InvalidModelSpecError,
    InvalidPromptError,
    ModelLoadError,
    ModelNotLoadedError,
)
from app.domain.inference.generation import (
    GenerationConfig,
    GenerationResult,
    TokenizationResult,
)
from app.domain.models.model_spec import ModelSpec

PINNED = "a10cc1512eabd3dde888204e902eca88bddb4951"
MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"


def test_model_spec_accepts_pinned_revision():
    spec = ModelSpec(model_id=MODEL_ID, revision=PINNED)
    assert spec.trust_remote_code is False


@pytest.mark.parametrize(
    "revision", ["", "main", "REPLACE_WITH_PINNED_REVISION", "a10cc15", PINNED.upper()]
)
def test_model_spec_rejects_unpinned_revision(revision):
    with pytest.raises(InvalidModelSpecError):
        ModelSpec(model_id=MODEL_ID, revision=revision)


def test_model_spec_rejects_trust_remote_code():
    with pytest.raises(InvalidModelSpecError):
        ModelSpec(model_id=MODEL_ID, revision=PINNED, trust_remote_code=True)


@pytest.mark.parametrize("model_id", ["", "no-slash", "../etc/passwd", "a/b/c", "/abs/path"])
def test_model_spec_rejects_bad_model_id(model_id):
    with pytest.raises(InvalidModelSpecError):
        ModelSpec(model_id=model_id, revision=PINNED)


def test_generation_config_default_is_64():
    assert GenerationConfig().max_new_tokens == 64


@pytest.mark.parametrize("value", [0, -1])
def test_generation_config_rejects_non_positive(value):
    with pytest.raises(InvalidGenerationConfigError):
        GenerationConfig(max_new_tokens=value)


def test_tokenization_result_count():
    assert TokenizationResult((1, 2, 3)).count == 3


def test_generation_result_fields():
    result = GenerationResult(text="hi", prompt_tokens=2, output_tokens=1)
    assert (result.text, result.prompt_tokens, result.output_tokens) == ("hi", 2, 1)


def test_all_domain_errors_derive_from_inferx_error():
    for error in (
        InvalidModelSpecError,
        InvalidPromptError,
        InvalidGenerationConfigError,
        ModelLoadError,
        ModelNotLoadedError,
        InferenceFailedError,
    ):
        assert issubclass(error, InferxError)
