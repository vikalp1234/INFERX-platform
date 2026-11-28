import pytest

from app.domain.exceptions import InvalidArchitectureError
from app.domain.inference.kv_cache import ModelArchitecture, estimate_kv_cache

ARCH = ModelArchitecture(num_layers=32, num_kv_heads=8, head_dim=64, dtype_bytes=2)


def test_formula_hand_computed():
    est = estimate_kv_cache(ARCH, tokens=100)
    assert est.bytes == 2 * 32 * 8 * 64 * 2 * 100 == 6_553_600
    assert est.tokens == 100


def test_zero_tokens_is_zero_bytes():
    assert estimate_kv_cache(ARCH, tokens=0).bytes == 0


def test_negative_tokens_rejected():
    with pytest.raises(InvalidArchitectureError):
        estimate_kv_cache(ARCH, tokens=-1)


@pytest.mark.parametrize("field", ["num_layers", "num_kv_heads", "head_dim", "dtype_bytes"])
@pytest.mark.parametrize("value", [0, -1])
def test_invalid_architecture_rejected(field, value):
    kwargs = {"num_layers": 1, "num_kv_heads": 1, "head_dim": 1, "dtype_bytes": 1, field: value}
    with pytest.raises(InvalidArchitectureError):
        ModelArchitecture(**kwargs)


def test_provenance_label_is_derived():
    assert estimate_kv_cache(ARCH, tokens=1).provenance == "derived_from_model_config"
