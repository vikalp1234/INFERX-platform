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
