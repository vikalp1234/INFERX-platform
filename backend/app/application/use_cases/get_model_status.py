from app.application.dto.model_status import ModelStatus
from app.application.ports.outbound.model_execution import ModelExecutionPort
from app.domain.models.model_spec import ModelSpec


class GetModelStatus:
    def __init__(self, execution: ModelExecutionPort, spec: ModelSpec) -> None:
        self._execution = execution
        self._spec = spec

    def execute(self) -> ModelStatus:
        return ModelStatus(
            loaded=self._execution.is_loaded(),
            model_id=self._spec.model_id,
            revision=self._spec.revision,
        )
