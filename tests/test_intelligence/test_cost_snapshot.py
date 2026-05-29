"""Testes do snapshot público de custo (T01 — M4)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from config.settings import Settings
from intelligence import CostSnapshot, get_cost_snapshot, reset_for_new_execution
from intelligence import llm as llm_module


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr("keyring.get_password", lambda service, key: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    llm_module._reset_client_for_tests()
    yield
    llm_module._reset_client_for_tests()


def test_sem_reset_retorna_zeros() -> None:
    snap = get_cost_snapshot()
    assert isinstance(snap, CostSnapshot)
    assert snap.tokens_in == 0
    assert snap.tokens_out == 0
    assert snap.cost_usd == 0.0


def test_apos_reset_retorna_zeros() -> None:
    reset_for_new_execution(Settings(_env_file=None))  # type: ignore[call-arg]
    snap = get_cost_snapshot()
    assert snap.tokens_in == 0
    assert snap.tokens_out == 0
    assert snap.cost_usd == 0.0


def test_reflete_uso_apos_add_after() -> None:
    reset_for_new_execution(Settings(_env_file=None))  # type: ignore[call-arg]
    assert llm_module._cost_tracker is not None
    llm_module._cost_tracker.add_after("gpt-4o-mini", 200, 100)
    snap = get_cost_snapshot()
    assert snap.tokens_in == 200
    assert snap.tokens_out == 100
    assert snap.cost_usd >= 0.0
