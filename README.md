# INFERX

**LLM Inference Engineering Platform — Understand. Measure. Optimize.**

INFERX is an open-source engineering platform to understand, inspect, measure, compare and optimize LLM inference and model serving. It is not just a chatbot.

> **Status: pre-release (v0.3.0 candidate).** Only the items marked IMPLEMENTED below exist; everything else is a roadmap target.

## Roadmap status

| Capability | Target | Status |
|---|---|---|
| Transformers inference | v0.1 | IMPLEMENTED (see [evidence](docs/v0.1.0-verification.md)) |
| Sampling controls, per-request timings, KV estimate | v0.2 | IMPLEMENTED (see [evidence](docs/v0.2.0-verification.md)) |
| HTTP API and SSE streaming (no auth; local use) | v0.3 | IMPLEMENTED (see [evidence](docs/v0.3.0-verification.md)) |
| Core learning platform | v1.0 | PLANNED |
| Repeatable benchmarks | v2.0 | PLANNED |
| Multi-engine adapters | v3.0 | PLANNED |
| RBAC and tenant isolation | v3.3 / v4.0 | PLANNED |
| Production operations | v4.0 | PLANNED |

Status changes only when code, tests or recorded evidence exist.

## Quick start (development)

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync                 # core dependencies only (no PyTorch)
uv run pytest           # unit and contract tests with a fake model
uv run uvicorn app.main:app   # GET /health -> {"status": "ok"}; API on 127.0.0.1:8000
```

To run a real model locally (downloads weights into your Hugging Face cache):

```bash
cp ../.env.example .env          # local, git-ignored
uv sync --extra ml
uv run python -m app.bootstrap.cli "The capital of France is"
uv run python -m app.bootstrap.cli "The capital of France is" --temperature 0.8 --seed 7 --metrics
uv run pytest -m model           # real-model contract tests
```

## HTTP API (local use only — no authentication)

```bash
INFERX_AUTOLOAD_MODEL=true uv run uvicorn app.main:app --host 127.0.0.1 --port 8000   # needs uv sync --extra ml
curl -N -X POST http://127.0.0.1:8000/v1/generate/stream \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "The capital of France is", "max_new_tokens": 16}'
```

Routes: `GET /health`, `GET /v1/model`, `POST /v1/tokenize`, `POST /v1/generate`, `POST /v1/generate/stream`. See the [API reference](docs/api.md).

## Documentation

- [API reference](docs/api.md) · [v0.3.0 verification](docs/v0.3.0-verification.md) · [v0.3.0 component graph](docs/architecture/v0.3.0-components.md)
- [Inference mechanics](docs/inference-mechanics.md) · [v0.2.0 verification](docs/v0.2.0-verification.md) · [v0.2.0 component graph](docs/architecture/v0.2.0-components.md) · [Notebook](notebooks/01_inference_mechanics.ipynb)
- [Approved models](docs/models.md) · [v0.1.0 verification](docs/v0.1.0-verification.md) · [v0.1.0 component graph](docs/architecture/v0.1.0-components.md)

- [Master implementation guide](docs/MASTER_IMPLEMENTATION_GUIDE.md)
- [Engineering rules (CLAUDE.md)](CLAUDE.md)
- [Security policy](docs/security-policy.md) and [reporting](SECURITY.md)
- [Contributing](CONTRIBUTING.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Changelog](CHANGELOG.md)

## License

Apache-2.0. Model weights and datasets carry their own, separate licenses.
