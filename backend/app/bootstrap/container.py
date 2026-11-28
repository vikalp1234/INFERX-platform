from dataclasses import dataclass

from app.adapters.outbound.inference.transformers_adapter import TransformersInferenceAdapter
from app.application.ports.outbound.model_execution import ModelExecutionPort
from app.application.use_cases.estimate_kv_cache import EstimateKvCache
from app.application.use_cases.generate_text import GenerateText
from app.application.use_cases.load_model import LoadModel
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


def build_container(settings: Settings, execution: ModelExecutionPort | None = None) -> Container:
    """Composition root: the only place concrete adapters are chosen."""
    execution = execution or TransformersInferenceAdapter()
    limits = settings.to_input_limits()
    return Container(
        settings=settings,
        execution=execution,
        load_model=LoadModel(execution),
        tokenize_prompt=TokenizePrompt(execution, limits),
        generate_text=GenerateText(execution, limits),
        estimate_kv_cache=EstimateKvCache(execution),
    )
