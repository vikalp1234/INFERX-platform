import threading

import pytest

from app.application.services.request_gate import GateConfig, RequestGate
from app.domain.exceptions import OverloadedError


def gate(max_concurrent=1, max_waiting=1, wait_timeout_s=2.0) -> RequestGate:
    return RequestGate(GateConfig(max_concurrent, max_waiting, wait_timeout_s))


def start_waiter(g: RequestGate):
    """Thread that acquires a slot and holds it until told to release."""
    acquired, release = threading.Event(), threading.Event()
    errors: list[Exception] = []

    def run():
        try:
            slot = g.acquire()
        except Exception as exc:
            errors.append(exc)
            acquired.set()
            return
        acquired.set()
        release.wait(5)
        slot.release()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, acquired, release, errors


def wait_until(predicate, timeout=2.0):
    done = threading.Event()
    deadline = threading.Timer(timeout, done.set)
    deadline.start()
    while not predicate() and not done.is_set():
        done.wait(0.005)
    deadline.cancel()
    return predicate()


def test_acquire_up_to_max_concurrent():
    g = gate(max_concurrent=2, max_waiting=0)
    a, b = g.acquire(), g.acquire()
    assert g.running == 2
    with pytest.raises(OverloadedError):
        g.acquire()
    a.release()
    b.release()
    assert g.running == 0


def test_waiter_gets_slot_after_release():
    g = gate()
    first = g.acquire()
    _, acquired, release, errors = start_waiter(g)
    assert wait_until(lambda: g.waiting == 1)
    first.release()
    assert acquired.wait(2)
    assert errors == []
    assert g.running == 1
    release.set()
    assert wait_until(lambda: g.running == 0)


def test_check_capacity_raises_when_busy_and_waiting_room_full():
    g = gate(max_concurrent=1, max_waiting=1)
    first = g.acquire()
    g.check_capacity()  # one waiting place left
    _, _, release, _ = start_waiter(g)
    assert wait_until(lambda: g.waiting == 1)
    with pytest.raises(OverloadedError):
        g.check_capacity()
    with pytest.raises(OverloadedError):
        g.acquire()
    first.release()
    release.set()


def test_check_capacity_ok_when_idle_even_with_zero_waiting_room():
    gate(max_concurrent=1, max_waiting=0).check_capacity()


def test_wait_timeout_raises_overloaded_and_clears_waiting():
    g = gate(max_concurrent=1, max_waiting=1, wait_timeout_s=0.05)
    g.acquire()
    with pytest.raises(OverloadedError):
        g.acquire()
    assert g.waiting == 0


def test_release_is_idempotent_and_never_over_releases():
    g = gate(max_concurrent=1, max_waiting=0)
    slot = g.acquire()
    slot.release()
    slot.release()
    assert g.running == 0
    g.acquire()
    assert g.running == 1


def test_slot_is_a_context_manager():
    g = gate()
    with g.acquire():
        assert g.running == 1
    assert g.running == 0
