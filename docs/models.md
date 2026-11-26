# Approved models

| Field | Value |
|---|---|
| Model ID | `HuggingFaceTB/SmolLM2-360M-Instruct` |
| Pinned revision | `a10cc1512eabd3dde888204e902eca88bddb4951` |
| License (model card metadata) | Apache-2.0 |
| Gated | No |
| Source | https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct |
| Metadata checked | 2026-11-26 via the Hugging Face API (model last modified 2025-09-22) |

## Notes

- The revision must be a 40-character lowercase commit SHA. INFERX rejects `main`, short SHAs and placeholders (`ModelSpec`).
- `trust_remote_code` is always `False`.
- Model **code** and **weights** carry separate licenses. The weights license above comes from the model card metadata; the maintainer must read the full model card before redistributing or hosting.
- Weights are downloaded into the Hugging Face cache on first load and are never committed (`.gitignore` blocks `*.safetensors`, `*.bin`, `*.gguf`, `/models/`, `huggingface/`).
- v0.1.0 sends raw prompts: no chat template is applied, and decoding is greedy.
- Hardware fit is unmeasured. Run one model at a time on small machines; measured results belong in `docs/v0.1.0-verification.md`.
