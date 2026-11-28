from dataclasses import dataclass

from app.adapters.outbound.inference.transformers_adapter import TransformersInferenceAdapter
from app.application.ports.outbound.model_execution import ModelExecutionPort
from app.application.services.request_gate import RequestGate
from app.application.use_cases.estimate_kv_cache import EstimateKvCache
from app.application.use_cases.generate_text import GenerateText
from app.application.use_cases.get_model_status import GetModelStatus
from app.application.use_cases.load_model import LoadModel
from app.application.use_cases.stream_generation import StreamGeneration
from app.application.use_cases.tokenize_prompt import TokenizePrompt
from app.infrastructure.config.settings import Settings


@dataclass
class Container:
    settings: Settings
    execution: ModelExecutionPort
    load_model: LoadModel
    tokenize_prompt: TokenizePrompt
    generate_text: GenerateText
    estimate_kv_cache: EstimateKvCache
    gate: RequestGate
    stream_generation: StreamGeneration
    get_model_status: GetModelStatus


def build_container(settings: Settings, execution: ModelExecutionPort | None = None) -> Container:
    """Composition root: the only place concrete adapters are chosen."""
    execution = execution or TransformersInferenceAdapter()
    limits = settings.to_input_limits()
    gate = RequestGate(settings.to_gate_config())
    return Container(
        settings=settings,
        execution=execution,
        load_model=LoadModel(execution),
        tokenize_prompt=TokenizePrompt(execution, limits),
        generate_text=GenerateText(execution, limits, gate),
        estimate_kv_cache=EstimateKvCache(execution),
        gate=gate,
        stream_generation=StreamGeneration(execution, limits, gate),
        get_model_status=GetModelStatus(execution, settings.to_model_spec()),
    )
