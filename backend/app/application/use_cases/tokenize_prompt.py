from app.application.dto.limits import InputLimits
from app.application.ports.outbound.model_execution import ModelExecutionPort
from app.application.use_cases.validation import validate_prompt
from app.domain.inference.generation import TokenizationResult


class TokenizePrompt:
    def __init__(self, execution: ModelExecutionPort, limits: InputLimits) -> None:
        self._execution = execution
        self._limits = limits

    def execute(self, prompt: str) -> TokenizationResult:
        validate_prompt(prompt, self._limits)
        return self._execution.tokenize(prompt)
