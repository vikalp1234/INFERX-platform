"""Command-line smoke tool: load the model, tokenize and generate.

Usage: uv run --extra ml python -m app.bootstrap.cli "Your prompt"
Exit codes: 0 success, 1 expected INFERX error, 2 unexpected error.
"""

import argparse
import json
import sys

from app.application.dto.metrics import RunMetrics
from app.bootstrap.container import Container, build_container
from app.domain.exceptions import InferxError
from app.domain.inference.generation import GenerationConfig
from app.infrastructure.config.settings import Settings
from app.infrastructure.observability.logging import configure_logging


def main(argv: list[str] | None = None, container: Container | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inferx-cli")
    parser.add_argument("prompt")
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.0, help="0 = greedy")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--repetition-penalty", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--metrics", action="store_true", help="print labelled run metrics JSON to stderr"
    )
    args = parser.parse_args(argv)

    try:
        container = container or build_container(Settings())
        configure_logging(container.settings.log_level, sys.stderr)
        container.load_model.execute(container.settings.to_model_spec())
        tokens = container.tokenize_prompt.execute(args.prompt)
        print(f"prompt_tokens: {tokens.count}")
        config = GenerationConfig(
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_k=args.top_k,
            top_p=args.top_p,
            repetition_penalty=args.repetition_penalty,
            seed=args.seed,
        )
        result = container.generate_text.execute(args.prompt, config)
        print(result.text)
        if args.metrics:
            kv = container.estimate_kv_cache.execute(result.prompt_tokens + result.output_tokens)
            metrics = RunMetrics.from_result(result, kv).to_dict()
            print(json.dumps({"metrics": metrics}), file=sys.stderr)
        return 0
    except InferxError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: unexpected failure ({type(exc).__name__})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
