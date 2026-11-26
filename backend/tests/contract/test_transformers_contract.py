import pytest

from app.adapters.outbound.inference.transformers_adapter import TransformersInferenceAdapter
from tests.contract.model_execution_contract import ModelExecutionContract

pytestmark = pytest.mark.model


class TestTransformersContract(ModelExecutionContract):
    def make_port(self):
        return TransformersInferenceAdapter()
