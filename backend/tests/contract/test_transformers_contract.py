import pytest

from app.adapters.outbound.inference.transformers_adapter import TransformersInferenceAdapter
from app.domain.exceptions import InferenceFailedError
from app.domain.inference.generation import GenerationConfig
from tests.contract.model_execution_contract import ModelExecutionContract

pytestmark = pytest.mark.model


class TestTransformersContract(ModelExecutionContract):
    def make_port(self):
        return TransformersInferenceAdapter()

    def test_one_token_output_has_none_tpot_and_tps(self, port):
        from tests.contract.model_execution_contract import VALID_SPEC

        port.load(VALID_SPEC)
        result = port.generate("The capital of France is", GenerationConfig(max_new_tokens=1))
        assert result.output_tokens == 1
        assert result.timings.ttft_ms is not None
        assert result.timings.tpot_ms is None
        assert result.timings.decode_tps is None

    def test_token_count_matches_timestamps_for_longer_output(self, port):
        from tests.contract.model_execution_contract import VALID_SPEC

        port.load(VALID_SPEC)
        result = port.generate("Count: one, two,", GenerationConfig(max_new_tokens=12))
        assert len(result.timings.token_timestamps_ns) == result.output_tokens
        assert result.timings.decode_tps is None or result.timings.decode_tps > 0

    def test_unseeded_sampling_does_not_raise(self, port):
        from tests.contract.model_execution_contract import VALID_SPEC

        port.load(VALID_SPEC)
        result = port.generate(
            "Hello", GenerationConfig(max_new_tokens=4, temperature=0.9, top_k=20, top_p=0.95)
        )
        assert result.output_tokens >= 1

    def test_runtime_failure_becomes_inference_failed_and_adapter_recovers(self, port, monkeypatch):
        from tests.contract.model_execution_contract import VALID_SPEC

        port.load(VALID_SPEC)
        real_generate = port._model.generate

        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(port._model, "generate", boom)
        with pytest.raises(InferenceFailedError):
            port.generate("Hello", GenerationConfig(max_new_tokens=2))
        monkeypatch.setattr(port._model, "generate", real_generate)
        assert port.generate("Hello", GenerationConfig(max_new_tokens=2)).output_tokens >= 1

    def test_seeded_run_restores_global_rng_state(self, port):
        import torch

        from tests.contract.model_execution_contract import VALID_SPEC

        port.load(VALID_SPEC)
        torch.manual_seed(123)
        expected = torch.rand(1).item()
        torch.manual_seed(123)
        port.generate("Hello", GenerationConfig(max_new_tokens=3, temperature=0.8, seed=99))
        assert torch.rand(1).item() == expected

    def test_stream_text_matches_generate_text_for_greedy(self, port):
        from app.domain.inference.streaming import StreamFinished, TokenDelta
        from tests.contract.model_execution_contract import VALID_SPEC

        port.load(VALID_SPEC)
        cfg = GenerationConfig(max_new_tokens=10)
        prompt = "The capital of France is"
        expected = port.generate(prompt, cfg).text
        items = list(port.stream_generate(prompt, cfg))
        streamed = "".join(i.text for i in items if isinstance(i, TokenDelta))
        assert streamed == expected
        assert isinstance(items[-1], StreamFinished)

    def test_stream_multibyte_never_emits_replacement_char(self, port):
        from app.domain.inference.streaming import TokenDelta
        from tests.contract.model_execution_contract import VALID_SPEC

        port.load(VALID_SPEC)
        items = port.stream_generate(
            "Reply with the emoji 🌍 and the word мир:", GenerationConfig(max_new_tokens=24)
        )
        deltas = [i for i in items if isinstance(i, TokenDelta)]
        assert deltas
        assert all("�" not in d.text for d in deltas)

    def test_finish_reason_length_when_limit_hit(self, port):
        from app.domain.inference.generation import FinishReason
        from tests.contract.model_execution_contract import VALID_SPEC

        port.load(VALID_SPEC)
        result = port.generate(
            "Once upon a time there was a dragon who", GenerationConfig(max_new_tokens=2)
        )
        assert result.finish_reason is FinishReason.LENGTH

    def test_stream_failure_becomes_inference_failed_and_adapter_recovers(self, port, monkeypatch):
        from tests.contract.model_execution_contract import VALID_SPEC

        port.load(VALID_SPEC)
        real_generate = port._model.generate

        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(port._model, "generate", boom)
        with pytest.raises(InferenceFailedError):
            list(port.stream_generate("Hello", GenerationConfig(max_new_tokens=2)))
        monkeypatch.setattr(port._model, "generate", real_generate)
        assert port.generate("Hello", GenerationConfig(max_new_tokens=2)).output_tokens >= 1
