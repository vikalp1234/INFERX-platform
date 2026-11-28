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


def test_generate_passes_sampling_config_to_port():
    fake = loaded_fake()
    cfg = GenerationConfig(max_new_tokens=3, temperature=0.7, top_k=10, top_p=0.9, seed=5)
    GenerateText(fake, LIMITS).execute("hello", cfg)
    assert fake.configs == [cfg]


def test_generate_logs_timing_numbers_but_no_text(caplog):
    marker = "PROMPT-MARKER-xyz"
    fake = loaded_fake()
    with caplog.at_level(logging.INFO):
        GenerateText(fake, LIMITS).execute(marker, GenerationConfig(max_new_tokens=3))
    record = next(r for r in caplog.records if r.message == "generation_completed")
    assert record.ttft_ms == 1.0
    assert record.total_ms == 4.0
    assert marker not in caplog.text
    assert "fake output" not in caplog.text


def test_estimate_kv_cache_matches_hand_computed_value():
    from app.application.use_cases.estimate_kv_cache import EstimateKvCache

    est = EstimateKvCache(loaded_fake()).execute(tokens=10)
    assert est.bytes == 2 * 2 * 2 * 4 * 2 * 10
    assert est.provenance == "derived_from_model_config"


def test_estimate_kv_cache_requires_loaded_model():
    from app.application.use_cases.estimate_kv_cache import EstimateKvCache

    with pytest.raises(ModelNotLoadedError):
        EstimateKvCache(FakeModelExecution()).execute(tokens=10)


def test_run_metrics_labels_provenance_and_none_for_single_token():
    from app.application.dto.metrics import RunMetrics
    from app.domain.inference.kv_cache import KvCacheEstimate

    result = loaded_fake().generate("a b", GenerationConfig(max_new_tokens=1))
    data = RunMetrics.from_result(result, KvCacheEstimate(bytes=64, tokens=3)).to_dict()
    assert data["ttft_ms"] == {"value": 1.0, "provenance": "measured"}
    assert data["tpot_ms"]["value"] is None
    assert data["decode_tps"]["value"] is None
    assert data["output_tokens"]["provenance"] == "measured"
    assert data["kv_cache_bytes_estimate"] == {
        "value": 64,
        "provenance": "derived_from_model_config",
    }


class TestStreamGeneration:
    def make(self, fake=None, **gate_kwargs):
        from app.application.services.request_gate import GateConfig, RequestGate
        from app.application.use_cases.stream_generation import StreamGeneration

        fake = fake or loaded_fake()
        cfg = {"max_concurrent": 1, "max_waiting": 1, "wait_timeout_s": 1.0, **gate_kwargs}
        gate = RequestGate(GateConfig(**cfg))
        return StreamGeneration(fake, LIMITS, gate), fake, gate

    def test_validates_before_touching_port_or_gate(self):
        uc, fake, gate = self.make()
        with pytest.raises(InvalidPromptError):
            uc.execute("   ", GenerationConfig(max_new_tokens=2))
        with pytest.raises(InvalidGenerationConfigError):
            uc.execute("hi", GenerationConfig(max_new_tokens=LIMITS.max_new_tokens + 1))
        assert fake.calls == []
        assert gate.running == 0

    def test_unloaded_model_raises_eagerly(self):
        uc, _, _ = self.make(FakeModelExecution())
        with pytest.raises(ModelNotLoadedError):
            uc.execute("hi", GenerationConfig(max_new_tokens=2))

    def test_streams_items_and_releases_slot(self):
        uc, _, gate = self.make()
        items = list(uc.execute("hi there", GenerationConfig(max_new_tokens=3)))
        assert len(items) == 4
        assert gate.running == 0

    def test_closing_early_releases_slot_and_closes_port_stream(self):
        uc, fake, gate = self.make()
        stream = uc.execute("hi", GenerationConfig(max_new_tokens=3))
        next(stream)
        assert gate.running == 1
        stream.close()
        assert gate.running == 0
        assert fake.streams_closed == 1

    def test_port_failure_mid_stream_releases_slot_and_propagates(self):
        uc, _, gate = self.make(loaded_fake(fail_after=1))
        with pytest.raises(InferenceFailedError):
            list(uc.execute("hi", GenerationConfig(max_new_tokens=3)))
        assert gate.running == 0

    def test_overloaded_before_stream_starts(self):
        from app.domain.exceptions import OverloadedError

        uc, _, gate = self.make(max_waiting=0)
        gate.acquire()
        with pytest.raises(OverloadedError):
            uc.execute("hi", GenerationConfig(max_new_tokens=2))

    def test_logs_no_text(self, caplog):
        marker = "PROMPT-MARKER-xyz"
        uc, _, _ = self.make()
        with caplog.at_level(logging.INFO):
            list(uc.execute(marker, GenerationConfig(max_new_tokens=3)))
        assert marker not in caplog.text
        assert "fake" not in caplog.text
        record = next(r for r in caplog.records if r.message == "stream_completed")
        assert record.finish_reason == "length"


def test_get_model_status_reflects_load_state():
    from app.application.use_cases.get_model_status import GetModelStatus

    fake = FakeModelExecution()
    uc = GetModelStatus(fake, SPEC)
    assert uc.execute().loaded is False
    fake.load(SPEC)
    status = uc.execute()
    assert (status.loaded, status.model_id, status.revision) == (True, SPEC.model_id, SPEC.revision)


def test_generate_text_with_gate_releases_slot_after_failure():
    from app.application.services.request_gate import GateConfig, RequestGate

    gate = RequestGate(GateConfig(1, 0, 1.0))
    uc = GenerateText(loaded_fake(fail_generate=True), LIMITS, gate)
    with pytest.raises(InferenceFailedError):
        uc.execute("hi", GenerationConfig(max_new_tokens=2))
    assert gate.running == 0
