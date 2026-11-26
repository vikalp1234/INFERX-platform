"""Hugging Face Transformers implementation of ModelExecutionPort.

torch/transformers are imported lazily so the module imports without the ``ml`` extra.
Limitations (v0.1.0): raw prompts (no chat template), greedy decoding, no timing capture.
"""

import gc
import threading
from typing import Any

from app.domain.exceptions import (
    InferenceFailedError,
    ModelLoadError,
    ModelNotLoadedError,
)
from app.domain.inference.generation import (
    GenerationConfig,
    GenerationResult,
    TokenizationResult,
)
from app.domain.models.model_spec import ModelSpec


class TransformersInferenceAdapter:
    def __init__(self, device: str = "cpu") -> None:
        self._device = device
        self._lock = threading.Lock()
        self._model: Any = None
        self._tokenizer: Any = None
        self._torch: Any = None

    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    def load(self, spec: ModelSpec) -> None:
        with self._lock:
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer
            except ImportError as exc:
                raise ModelLoadError(
                    "ML dependencies are not installed; run: uv sync --extra ml"
                ) from exc
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    spec.model_id, revision=spec.revision, trust_remote_code=False
                )
                model = AutoModelForCausalLM.from_pretrained(
                    spec.model_id, revision=spec.revision, trust_remote_code=False
                )
                model.to(self._device)
                model.eval()
            except Exception as exc:
                self._reset()
                raise ModelLoadError(f"model could not be loaded ({type(exc).__name__})") from exc
            self._torch = torch
            self._tokenizer = tokenizer
            self._model = model

    def unload(self) -> None:
        with self._lock:
            self._reset()

    def tokenize(self, text: str) -> TokenizationResult:
        self._require_loaded()
        try:
            ids = self._tokenizer(text)["input_ids"]
        except Exception as exc:
            raise InferenceFailedError(f"tokenization failed ({type(exc).__name__})") from exc
        return TokenizationResult(tuple(int(i) for i in ids))

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        self._require_loaded()
        with self._lock:
            try:
                inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
                prompt_tokens = int(inputs["input_ids"].shape[1])
                with self._torch.inference_mode():
                    output = self._model.generate(
                        **inputs,
                        max_new_tokens=config.max_new_tokens,
                        do_sample=False,
                        pad_token_id=self._tokenizer.eos_token_id,
                    )
                new_ids = output[0][prompt_tokens:]
                text = self._tokenizer.decode(new_ids, skip_special_tokens=True)
            except Exception as exc:
                raise InferenceFailedError(f"generation failed ({type(exc).__name__})") from exc
        return GenerationResult(
            text=text, prompt_tokens=prompt_tokens, output_tokens=int(new_ids.shape[0])
        )

    def _require_loaded(self) -> None:
        if not self.is_loaded():
            raise ModelNotLoadedError("model is not loaded")

    def _reset(self) -> None:
        self._model = None
        self._tokenizer = None
        self._torch = None
        gc.collect()
