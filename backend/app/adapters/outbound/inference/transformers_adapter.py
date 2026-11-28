"""Hugging Face Transformers implementation of ModelExecutionPort.

torch/transformers are imported lazily so the module imports without the ``ml`` extra.
Limitations (v0.3.0): raw prompts (no chat template), no stop sequences.

Streaming: ``stream_generate`` runs the model in a worker thread that holds the adapter lock;
text deltas come from incremental decoding (withheld while the tail is an incomplete
multi-byte character). Closing the iterator or setting ``cancel`` stops generation at the
next token via a StoppingCriteria.

Timing boundary: the request-start stamp is taken once the adapter lock is held, before
tokenization (so tokenization and device transfer are INCLUDED, lock wait is EXCLUDED).
One stamp is recorded each time the generation loop emits a token. Transformers does not
expose a separate prefill timer, so TTFT covers prefill plus first-token selection.

Seeding: a seeded request runs inside ``torch.random.fork_rng`` so the global RNG state is
restored afterwards; unseeded requests never touch the RNG.
"""

import gc
import queue
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

from app.domain.exceptions import (
    InferenceFailedError,
    ModelLoadError,
    ModelNotLoadedError,
)
from app.domain.inference.generation import (
    FinishReason,
    GenerationConfig,
    GenerationResult,
    TokenizationResult,
)
from app.domain.inference.kv_cache import ModelArchitecture
from app.domain.inference.streaming import StreamFinished, StreamItem, TokenDelta
from app.domain.inference.timings import GenerationTimings
from app.domain.models.model_spec import ModelSpec

_JOIN_TIMEOUT_S = 30.0


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
                streamer = self._make_streamer()
                run = self._run(prompt, config, streamer, criteria=None)
                return self._build_result(run, streamer.stamps, config, cancelled=False)
            except Exception as exc:
                raise InferenceFailedError(f"generation failed ({type(exc).__name__})") from exc

    def stream_generate(
        self, prompt: str, config: GenerationConfig, cancel: threading.Event | None = None
    ) -> Iterator[StreamItem]:
        self._require_loaded()
        events: queue.Queue[tuple[Any, ...]] = queue.Queue()
        stop = threading.Event()
        criteria = self._make_stop_criteria(stop, cancel)

        def worker() -> None:
            with self._lock:
                try:
                    streamer = self._make_streamer(lambda tid, ts: events.put(("tok", tid, ts)))
                    run = self._run(prompt, config, streamer, criteria)
                    result = self._build_result(
                        run, streamer.stamps, config, cancelled=criteria.triggered
                    )
                    events.put(("done", result, run.new_ids))
                except Exception as exc:
                    events.put(("error", exc))

        thread = threading.Thread(target=worker, name="inferx-stream", daemon=True)
        thread.start()
        ids: list[int] = []
        emitted = ""
        index = 0
        try:
            while True:
                kind, *payload = events.get()
                if kind == "tok":
                    ids.append(payload[0])
                    text = self._decode(ids)
                    if text.endswith("\ufffd") or not text.startswith(emitted):
                        continue  # incomplete multi-byte character: wait for more tokens
                    if len(text) > len(emitted):
                        yield TokenDelta(index, text[len(emitted) :])
                        index += 1
                        emitted = text
                elif kind == "done":
                    result = payload[0]
                    if len(result.text) > len(emitted) and result.text.startswith(emitted):
                        yield TokenDelta(index, result.text[len(emitted) :])
                    yield StreamFinished(result)
                    return
                else:
                    exc = payload[0]
                    raise InferenceFailedError(f"generation failed ({type(exc).__name__})") from exc
        finally:
            stop.set()
            thread.join(timeout=_JOIN_TIMEOUT_S)

    def _run(self, prompt: str, config: GenerationConfig, streamer: Any, criteria: Any) -> "_Run":
        """Run one generation. The caller must hold the adapter lock."""
        start_ns = time.perf_counter_ns()
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
        prompt_tokens = int(inputs["input_ids"].shape[1])
        extra: dict[str, Any] = {}
        if criteria is not None:
            from transformers import StoppingCriteriaList

            extra["stopping_criteria"] = StoppingCriteriaList([criteria])
        with self._torch.inference_mode(), self._seed_scope(config.seed):
            output = self._model.generate(
                **inputs,
                streamer=streamer,
                pad_token_id=self._tokenizer.eos_token_id,
                **self._sampling_kwargs(config),
                **extra,
            )
        new_ids = [int(i) for i in output[0][prompt_tokens:]]
        return _Run(start_ns, prompt_tokens, new_ids, time.perf_counter_ns())

    def _build_result(
        self, run: "_Run", stamps: list[int], config: GenerationConfig, cancelled: bool
    ) -> GenerationResult:
        if len(stamps) != len(run.new_ids):
            raise RuntimeError("token timestamp count mismatch")
        timings = GenerationTimings(
            run.start_ns, tuple(stamps), max(run.end_ns, *stamps, run.start_ns)
        )
        return GenerationResult(
            text=self._decode(run.new_ids),
            prompt_tokens=run.prompt_tokens,
            output_tokens=len(run.new_ids),
            timings=timings,
            finish_reason=self._finish_reason(run.new_ids, config, cancelled),
        )

    def _finish_reason(
        self, new_ids: list[int], config: GenerationConfig, cancelled: bool
    ) -> FinishReason:
        if cancelled:
            return FinishReason.CANCELLED
        eos = self._model.generation_config.eos_token_id
        eos_ids = set(eos) if isinstance(eos, list | tuple) else {eos}
        if new_ids and new_ids[-1] in eos_ids:
            return FinishReason.STOP
        return FinishReason.LENGTH

    def _decode(self, ids: list[int]) -> str:
        return self._tokenizer.decode(ids, skip_special_tokens=True)

    def _make_stop_criteria(self, stop: threading.Event, cancel: threading.Event | None) -> Any:
        from transformers import StoppingCriteria

        torch = self._torch

        class _CancelCriteria(StoppingCriteria):
            triggered = False

            def __call__(self, input_ids: Any, scores: Any, **kwargs: Any) -> Any:
                flag = stop.is_set() or (cancel is not None and cancel.is_set())
                if flag:
                    self.triggered = True
                return torch.full(
                    (input_ids.shape[0],), flag, dtype=torch.bool, device=input_ids.device
                )

        return _CancelCriteria()

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

    def _make_streamer(self, on_token: Callable[[int, int], None] | None = None) -> Any:
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
                ids = value.reshape(-1).tolist()
                for token_id in ids:
                    self.stamps.append(stamp)
                    if on_token is not None:
                        on_token(int(token_id), stamp)

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


@dataclass(frozen=True)
class _Run:
    start_ns: int
    prompt_tokens: int
    new_ids: list[int]
    end_ns: int


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
