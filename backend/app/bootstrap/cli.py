"""Command-line smoke tool: load the model, tokenize and generate.

Usage: uv run --extra ml python -m app.bootstrap.cli "Your prompt"
Exit codes: 0 success, 1 expected INFERX error, 2 unexpected error.
"""

import argparse
import sys

from app.bootstrap.container import Container, build_container
from app.domain.exceptions import InferxError
from app.domain.inference.generation import GenerationConfig
from app.infrastructure.config.settings import Settings
from app.infrastructure.observability.logging import configure_logging


def main(argv: list[str] | None = None, container: Container | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inferx-cli")
    parser.add_argument("prompt")
    parser.add_argument("--max-new-tokens", type=int, default=64)
    args = parser.parse_args(argv)

    try:
        container = container or build_container(Settings())
        configure_logging(container.settings.log_level, sys.stderr)
        container.load_model.execute(container.settings.to_model_spec())
        tokens = container.tokenize_prompt.execute(args.prompt)
        print(f"prompt_tokens: {tokens.count}")
        result = container.generate_text.execute(
            args.prompt, GenerationConfig(max_new_tokens=args.max_new_tokens)
        )
        print(result.text)
        return 0
    except InferxError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: unexpected failure ({type(exc).__name__})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
