from app.application.dto.limits import InputLimits
from app.domain.exceptions import InvalidPromptError


def validate_prompt(prompt: str, limits: InputLimits) -> None:
    if not prompt.strip():
        raise InvalidPromptError("prompt must not be empty")
    if len(prompt) > limits.max_prompt_chars:
        raise InvalidPromptError(f"prompt exceeds {limits.max_prompt_chars} characters")
