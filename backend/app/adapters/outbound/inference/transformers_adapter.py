"""Hugging Face Transformers implementation of ModelExecutionPort.

torch/transformers are imported lazily so the module imports without the ``ml`` extra.
Limitations (v0.2.0): raw prompts (no chat template), no stop sequences.

Timing boundary: the request-start stamp is taken once the adapter lock is held, before
tokenization (so tokenization and device transfer are INCLUDED, lock wait is EXCLUDED).
One stamp is recorded each time the generation loop emits a token. Transformers does not
expose a separate prefill timer, so TTFT covers prefill plus first-token selection.

Seeding: a seeded request runs inside ``torch.random.fork_rng`` so the global RNG state is
restored afterwards; unseeded requests never touch the RNG.
"""

import gc
import threading
import time
from contextlib import nullcontext
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
from app.domain.inference.kv_cache import ModelArchitecture
from app.domain.inference.timings import GenerationTimings
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
            start_ns = time.perf_counter_ns()
            try:
                inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
                prompt_tokens = int(inputs["input_ids"].shape[1])
                streamer = self._make_streamer()
                with self._torch.inference_mode(), self._seed_scope(config.seed):
                    output = self._model.generate(
                        **inputs,
                        streamer=streamer,
                        pad_token_id=self._tokenizer.eos_token_id,
                        **self._sampling_kwargs(config),
                    )
                new_ids = output[0][prompt_tokens:]
                text = self._tokenizer.decode(new_ids, skip_special_tokens=True)
                end_ns = time.perf_counter_ns()
                stamps = tuple(streamer.stamps)
                output_tokens = int(new_ids.shape[0])
                if len(stamps) != output_tokens:
                    raise RuntimeError("token timestamp count mismatch")
                timings = GenerationTimings(start_ns, stamps, max(end_ns, *stamps, start_ns))
            except Exception as exc:
                raise InferenceFailedError(f"generation failed ({type(exc).__name__})") from exc
        return GenerationResult(
            text=text, prompt_tokens=prompt_tokens, output_tokens=output_tokens, timings=timings
        )

    def architecture(self) -> ModelArchitecture:
        self._require_loaded()
        try:
            cfg = self._model.config
            heads = cfg.num_attention_heads
            return ModelArchitecture(
                num_layers=int(cfg.num_hidden_layers),
                num_kv_heads=int(getattr(cfg, "num_key_value_heads", None) or heads),
                head_dim=int(getattr(cfg, "head_dim", None) or cfg.hidden_size // heads),
                dtype_bytes=int(self._torch.empty((), dtype=self._model.dtype).element_size()),
            )
        except Exception as exc:
            raise InferenceFailedError(
                f"architecture lookup failed ({type(exc).__name__})"
            ) from exc

    @staticmethod
    def _sampling_kwargs(config: GenerationConfig) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"max_new_tokens": config.max_new_tokens}
        if config.is_greedy:
            kwargs["do_sample"] = False
        else:
            kwargs.update(do_sample=True, temperature=config.temperature)
            if config.top_k is not None:
                kwargs["top_k"] = config.top_k
            if config.top_p is not None:
                kwargs["top_p"] = config.top_p
        if config.repetition_penalty != 1.0:
            kwargs["repetition_penalty"] = config.repetition_penalty
        return kwargs

    def _seed_scope(self, seed: int | None) -> Any:
        if seed is None:
            return nullcontext()
        return _SeedScope(self._torch, seed, self._device)

    def _make_streamer(self) -> Any:
        from transformers.generation.streamers import BaseStreamer

        class _StampStreamer(BaseStreamer):
            def __init__(self) -> None:
                self.stamps: list[int] = []
                self._prompt_seen = False

            def put(self, value: Any) -> None:
                stamp = time.perf_counter_ns()
                if not self._prompt_seen:
                    self._prompt_seen = True  # first call carries the prompt ids
                    return
                self.stamps.append(stamp)

            def end(self) -> None:
                pass

        return _StampStreamer()

    def _require_loaded(self) -> None:
        if not self.is_loaded():
            raise ModelNotLoadedError("model is not loaded")

    def _reset(self) -> None:
        self._model = None
        self._tokenizer = None
        self._torch = None
        gc.collect()


class _SeedScope:
    """Seed torch for one generation call and restore the previous RNG state."""

    def __init__(self, torch: Any, seed: int, device: str) -> None:
        self._torch = torch
        self._seed = seed
        self._devices = [torch.device(device)] if str(device).startswith("cuda") else []
        self._fork: Any = None

    def __enter__(self) -> None:
        self._fork = self._torch.random.fork_rng(devices=self._devices)
        self._fork.__enter__()
        self._torch.manual_seed(self._seed)

    def __exit__(self, *exc_info: Any) -> Any:
        return self._fork.__exit__(*exc_info)
