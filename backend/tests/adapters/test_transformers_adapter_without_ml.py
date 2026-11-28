import importlib.util

import pytest

from app.adapters.outbound.inference.transformers_adapter import TransformersInferenceAdapter
from app.domain.exceptions import ModelLoadError
from app.domain.models.model_spec import ModelSpec

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("torch") is not None, reason="ml extra is installed"
)


def test_load_without_ml_extra_raises_model_load_error_with_hint():
    adapter = TransformersInferenceAdapter()
    spec = ModelSpec(
        "HuggingFaceTB/SmolLM2-360M-Instruct", "a10cc1512eabd3dde888204e902eca88bddb4951"
    )
    with pytest.raises(ModelLoadError, match="uv sync --extra ml"):
        adapter.load(spec)
    assert adapter.is_loaded() is False
