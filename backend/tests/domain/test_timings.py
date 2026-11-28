import pytest

from app.domain.exceptions import InvalidTimingError
from app.domain.inference.generation import GenerationResult
from app.domain.inference.timings import GenerationTimings

MS = 1_000_000


def test_metrics_match_hand_computed_values():
    t = GenerationTimings(
        request_start_ns=0,
        token_timestamps_ns=(100 * MS, 150 * MS, 200 * MS, 250 * MS),
        end_ns=260 * MS,
    )
    assert t.ttft_ms == 100.0
    assert t.tpot_ms == 50.0
    assert t.decode_tps == 20.0
    assert t.total_ms == 260.0


def test_single_token_tpot_and_tps_are_none():
    t = GenerationTimings(0, (80 * MS,), 90 * MS)
    assert t.ttft_ms == 80.0
    assert t.tpot_ms is None
    assert t.decode_tps is None


def test_zero_tokens_ttft_none_but_total_computed():
    t = GenerationTimings(0, (), 30 * MS)
    assert t.ttft_ms is None
    assert t.tpot_ms is None
    assert t.decode_tps is None
    assert t.total_ms == 30.0


def test_identical_first_and_last_stamp_gives_none_tps():
    t = GenerationTimings(0, (10 * MS, 10 * MS), 11 * MS)
    assert t.tpot_ms == 0.0
    assert t.decode_tps is None


@pytest.mark.parametrize(
    ("start", "tokens", "end"),
    [
        (100, (50,), 200),
        (0, (30, 20), 100),
        (0, (10, 20), 15),
    ],
)
def test_non_monotonic_stamps_rejected(start, tokens, end):
    with pytest.raises(InvalidTimingError):
        GenerationTimings(start, tokens, end)


def test_result_timings_default_none():
    assert GenerationResult("x", 1, 1).timings is None
