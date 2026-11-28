import logging

from app.application.ports.outbound.model_execution import ModelExecutionPort
from app.domain.models.model_spec import ModelSpec

logger = logging.getLogger(__name__)


class LoadModel:
    def __init__(self, execution: ModelExecutionPort) -> None:
        self._execution = execution

    def execute(self, spec: ModelSpec) -> None:
        extra = {"model_id": spec.model_id, "revision": spec.revision}
        logger.info("model_load_started", extra=extra)
        try:
            self._execution.load(spec)
        except Exception as exc:
            logger.error("model_load_failed", extra={**extra, "error_type": type(exc).__name__})
            raise
        logger.info("model_load_succeeded", extra=extra)
