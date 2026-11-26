import re
from dataclasses import dataclass

from app.domain.exceptions import InvalidModelSpecError

_MODEL_ID = re.compile(r"[A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*")
_REVISION = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True)
class ModelSpec:
    """An approved model pinned to an immutable 40-hex commit revision."""

    model_id: str
    revision: str
    trust_remote_code: bool = False

    def __post_init__(self) -> None:
        if not _MODEL_ID.fullmatch(self.model_id):
            raise InvalidModelSpecError("model_id must look like 'owner/name'")
        if not _REVISION.fullmatch(self.revision):
            raise InvalidModelSpecError("revision must be a pinned 40-character lowercase hex SHA")
        if self.trust_remote_code:
            raise InvalidModelSpecError("trust_remote_code is not allowed")
