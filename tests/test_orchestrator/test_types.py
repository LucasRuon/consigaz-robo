"""Testes de `orchestrator.types`."""

from __future__ import annotations

import dataclasses

import pytest

from intelligence.types import Action
from orchestrator.types import RoutineResult


def test_routine_result_construcao_minima() -> None:
    r = RoutineResult(action=Action.PROCEED_TO_WEB)
    assert r.action is Action.PROCEED_TO_WEB
    assert r.evidence == {}
    assert r.exit_code_hint is None


def test_routine_result_eh_frozen() -> None:
    r = RoutineResult(action=Action.ABORT_IN_DESKTOP)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.action = Action.PROCEED_TO_WEB  # type: ignore[misc]


def test_routine_result_aceita_qualquer_action() -> None:
    for action in Action:
        r = RoutineResult(action=action, evidence={"k": 1}, exit_code_hint=7)
        assert r.action is action
        assert r.exit_code_hint == 7
