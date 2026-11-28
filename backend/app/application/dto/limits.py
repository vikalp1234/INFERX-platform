from dataclasses import dataclass


@dataclass(frozen=True)
class InputLimits:
    max_prompt_chars: int
    max_new_tokens: int
