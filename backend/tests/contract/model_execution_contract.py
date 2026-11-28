"""Shared behavior every ModelExecutionPort implementation must satisfy."""

import threading

import pytest

from app.domain.exceptions import ModelLoadError, ModelNotLoadedError
from app.domain.inference.generation import FinishReason, GenerationConfig
from app.domain.inference.streaming import StreamFinished, TokenDelta
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

    def test_generate_returns_timings_with_one_stamp_per_token(self, port):
        port.load(VALID_SPEC)
        result = port.generate("The capital of France is", GenerationConfig(max_new_tokens=4))
        assert result.timings is not None
        assert len(result.timings.token_timestamps_ns) == result.output_tokens

    def test_timestamps_are_monotonic(self, port):
        port.load(VALID_SPEC)
        result = port.generate("The capital of France is", GenerationConfig(max_new_tokens=4))
        stamps = (
            result.timings.request_start_ns,
            *result.timings.token_timestamps_ns,
            result.timings.end_ns,
        )
        assert list(stamps) == sorted(stamps)

    def test_architecture_requires_loaded_model(self, port):
        with pytest.raises(ModelNotLoadedError):
            port.architecture()

    def test_architecture_after_load_has_positive_fields(self, port):
        port.load(VALID_SPEC)
        arch = port.architecture()
        assert arch.num_layers >= 1
        assert arch.num_kv_heads >= 1
        assert arch.head_dim >= 1
        assert arch.dtype_bytes >= 1

    def test_same_seed_same_text(self, port):
        port.load(VALID_SPEC)
        cfg = GenerationConfig(max_new_tokens=6, temperature=0.8, seed=7)
        first = port.generate("The capital of France is", cfg)
        second = port.generate("The capital of France is", cfg)
        assert first.text == second.text

    def test_greedy_ignores_seed_and_is_stable(self, port):
        port.load(VALID_SPEC)
        prompt = "The capital of France is"
        a = port.generate(prompt, GenerationConfig(max_new_tokens=5, seed=1))
        b = port.generate(prompt, GenerationConfig(max_new_tokens=5, seed=2))
        assert a.text == b.text

    def test_stream_yields_deltas_then_one_finish(self, port):
        port.load(VALID_SPEC)
        items = list(
            port.stream_generate("The capital of France is", GenerationConfig(max_new_tokens=6))
        )
        deltas, last = items[:-1], items[-1]
        assert isinstance(last, StreamFinished)
        assert all(isinstance(d, TokenDelta) for d in deltas)
        assert [d.index for d in deltas] == list(range(len(deltas)))
        assert last.result.finish_reason in set(FinishReason)
        assert "".join(d.text for d in deltas) == last.result.text

    def test_stream_before_load_raises(self, port):
        with pytest.raises(ModelNotLoadedError):
            next(iter(port.stream_generate("hello", GenerationConfig(max_new_tokens=2))))

    def test_stream_cancel_event_ends_with_cancelled(self, port):
        port.load(VALID_SPEC)
        cancel = threading.Event()
        stream = port.stream_generate(
            "Write a long story about a dragon.", GenerationConfig(max_new_tokens=48), cancel
        )
        items = []
        for item in stream:
            items.append(item)
            if isinstance(item, TokenDelta):
                cancel.set()
        assert isinstance(items[-1], StreamFinished)
        assert items[-1].result.finish_reason is FinishReason.CANCELLED
        assert items[-1].result.output_tokens < 48

    def test_closing_stream_early_allows_next_generate(self, port):
        port.load(VALID_SPEC)
        stream = port.stream_generate(
            "Write a long story about a dragon.", GenerationConfig(max_new_tokens=48)
        )
        next(stream)
        stream.close()
        result = port.generate("Hello", GenerationConfig(max_new_tokens=2))
        assert result.output_tokens >= 1
