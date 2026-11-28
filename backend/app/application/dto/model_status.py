from dataclasses import dataclass


@dataclass(frozen=True)
class ModelStatus:
    loaded: bool
    model_id: str
    revision: str
