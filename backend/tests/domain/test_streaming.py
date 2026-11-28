from app.domain.inference.generation import FinishReason, GenerationResult
from app.domain.inference.streaming import StreamFinished, TokenDelta


def test_finish_reason_values():
    assert [r.value for r in FinishReason] == ["stop", "length", "cancelled"]


def test_result_finish_reason_defaults_to_none():
    assert GenerationResult("x", 1, 1).finish_reason is None


def test_stream_items_are_value_objects():
    assert TokenDelta(0, "a") == TokenDelta(0, "a")
    result = GenerationResult("a", 1, 1, finish_reason=FinishReason.STOP)
    assert StreamFinished(result).result.finish_reason is FinishReason.STOP
