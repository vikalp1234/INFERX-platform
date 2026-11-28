# Inference mechanics (v0.2.0)

Every statement below is tagged **CONCEPTUAL** (explanation, no runtime value), **DERIVED** (computed from model configuration) or **MEASURED** (observed by the adapter at runtime). This file contains no performance numbers; measured figures live only in dated verification records such as [v0.2.0-verification.md](v0.2.0-verification.md).

## Prefill and decode — CONCEPTUAL

Generation has two phases. **Prefill** processes the whole prompt in one forward pass and fills the KV cache. **Decode** then produces one token per forward pass, each pass reading the cache and appending to it. Prefill cost grows with prompt length; decode cost accumulates per output token.

## KV cache — CONCEPTUAL, with a DERIVED size estimate

Attention needs the keys and values of all earlier tokens. Caching them avoids recomputation at the price of memory that grows linearly with sequence length.

INFERX reports an estimate computed as `2 × layers × kv_heads × head_dim × dtype_bytes × tokens` (the 2 covers keys and values). It is **derived from model config**, labelled `derived_from_model_config`, and is not a reading of allocator memory; real engines add padding, block allocation and overhead.

## Sampling controls

| Control | Supported | Notes |
|---|---|---|
| `temperature` | yes | `0` means greedy decoding |
| `top_k`, `top_p` | yes | require `temperature > 0`; combined with greedy they are rejected, not ignored |
| `repetition_penalty` | yes | `1.0` disables it |
| `seed` | yes | reproducible text for the same prompt, config, runtime and hardware; global RNG state is restored afterwards |
| stop sequences | no | planned for v1.2.x |

## Metric definitions — MEASURED

Stamps come from `time.perf_counter_ns()`.

- `TTFT = first_token_time − request_start`
- `TPOT = (last_token_time − first_token_time) / (output_tokens − 1)`, only when `output_tokens > 1`
- `Decode TPS = (output_tokens − 1) / (last_token_time − first_token_time)`, only when the denominator is positive
- With one output token, TPOT and decode TPS are `null`, never zero. With zero output tokens, TTFT is also `null`.
- `total_ms = end − request_start`.

### Request-start boundary

`request_start` is taken once the adapter holds its lock. It **includes** tokenization and host-to-device transfer and **excludes** waiting for the lock (queue wait). Values are adapter-observed, not client-observed; network and API overhead are outside them (the HTTP API arrives in v0.3.0).

## What is measured, derived, conceptual

| Item | Class |
|---|---|
| prompt / output token counts | MEASURED |
| TTFT, TPOT, decode TPS, total time, raw per-token stamps | MEASURED |
| KV-cache bytes | DERIVED |
| prefill/decode and KV-cache explanations | CONCEPTUAL |

## Limitations

- Transformers exposes no separate prefill timer, so TTFT covers prefill plus first-token selection.
- Each token stamp is taken when the generation loop emits the token to the streamer, so it includes loop overhead.
- One run is a single sample; percentiles and benchmark protocol arrive in v2.0.0.
- Prompts are raw text (no chat template).
