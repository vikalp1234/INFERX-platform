"""Shared behavior every ModelExecutionPort implementation must satisfy."""

import pytest

from app.domain.exceptions import ModelLoadError, ModelNotLoadedError
from app.domain.inference.generation import GenerationConfig
from app.domain.models.model_spec import ModelSpec

PINNED = "a10cc1512eabd3dde888204e902eca88bddb4951"
VALID_SPEC = ModelSpec("HuggingFaceTB/SmolLM2-360M-Instruct", PINNED)
MISSING_SPEC = ModelSpec("invalid/does-not-exist", PINNED)


class ModelExecutionContract:
    def make_port(self):
        raise NotImplementedError

    @pytest.fixture
    def port(self):
        port = self.make_port()
        yield port
        port.unload()

    def test_not_loaded_initially(self, port):
        assert port.is_loaded() is False

    def test_operations_before_load_raise(self, port):
        with pytest.raises(ModelNotLoadedError):
            port.tokenize("hello")
        with pytest.raises(ModelNotLoadedError):
            port.generate("hello", GenerationConfig(max_new_tokens=2))

    def test_load_then_tokenize(self, port):
        port.load(VALID_SPEC)
        assert port.is_loaded() is True
        assert port.tokenize("hello world").count > 0

    def test_unicode_prompt_tokenizes(self, port):
        port.load(VALID_SPEC)
        assert port.tokenize("héllo 🌍 мир").count > 0

    def test_generate_within_limit_and_counts_match(self, port):
        port.load(VALID_SPEC)
        prompt = "The capital of France is"
        result = port.generate(prompt, GenerationConfig(max_new_tokens=5))
        assert 1 <= result.output_tokens <= 5
        assert result.prompt_tokens == port.tokenize(prompt).count

    def test_operations_after_unload_raise_and_unload_is_idempotent(self, port):
        port.load(VALID_SPEC)
        port.unload()
        port.unload()
        assert port.is_loaded() is False
        with pytest.raises(ModelNotLoadedError):
            port.tokenize("hello")

    def test_failed_load_stays_unloaded_and_retry_succeeds(self, port):
        with pytest.raises(ModelLoadError):
            port.load(MISSING_SPEC)
        assert port.is_loaded() is False
        port.load(VALID_SPEC)
        assert port.is_loaded() is True
