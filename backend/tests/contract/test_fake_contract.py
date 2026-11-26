from tests.contract.model_execution_contract import ModelExecutionContract
from tests.fakes.fake_model_execution import FakeModelExecution


class TestFakeContract(ModelExecutionContract):
    def make_port(self):
        return FakeModelExecution()
