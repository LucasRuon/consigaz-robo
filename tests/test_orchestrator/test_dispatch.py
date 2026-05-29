"""Testes de `orchestrator.dispatch`."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

import orchestrator.dispatch  # noqa: F401 — carrega submódulo em sys.modules
from config import Settings
from intelligence import llm as llm_module
from intelligence.types import Action
from orchestrator import registry
from orchestrator.boot import BootContext
from orchestrator.context import RoutineContext
from orchestrator.types import RoutineResult
from platform_info import Platform

dispatch_mod = sys.modules["orchestrator.dispatch"]


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr("keyring.get_password", lambda service, key: None)
    for var in ("OPENAI_API_KEY", "DESKTOP_APP_PASSWORD", "WEB_PLATFORM_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    registry._clear()
    llm_module._reset_client_for_tests()
    yield
    registry._clear()
    llm_module._reset_client_for_tests()


def _boot() -> BootContext:
    return BootContext(
        platform=Platform.DARWIN,
        settings=Settings(_env_file=None),  # type: ignore[call-arg]
        routine="r",
        log_dir=Path("logs"),
    )


@pytest.mark.parametrize(
    "action,expected",
    [
        (Action.PROCEED_TO_WEB, 0),
        (Action.ABORT_IN_DESKTOP, 5),
        (Action.RAISE_EXCEPTION, 5),
    ],
)
def test_dispatch_mapeia_action_para_exit(action: Action, expected: int) -> None:
    @registry.register("r")
    def run(ctx: RoutineContext) -> RoutineResult:
        return RoutineResult(action=action)

    code = dispatch_mod.dispatch("r", _boot(), dry_run=False)
    assert code == expected


def test_exit_code_hint_sobrescreve_default() -> None:
    @registry.register("r")
    def run(ctx: RoutineContext) -> RoutineResult:
        return RoutineResult(action=Action.ABORT_IN_DESKTOP, exit_code_hint=42)

    assert dispatch_mod.dispatch("r", _boot(), dry_run=False) == 42


def test_dispatch_propaga_excecao_da_rotina() -> None:
    @registry.register("r")
    def run(ctx: RoutineContext) -> RoutineResult:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        dispatch_mod.dispatch("r", _boot(), dry_run=False)


def test_reset_chamado_antes_da_rotina(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[str] = []

    real_reset = dispatch_mod.reset_for_new_execution

    def tracking_reset(settings):
        chamadas.append("reset")
        real_reset(settings)

    monkeypatch.setattr(dispatch_mod, "reset_for_new_execution", tracking_reset)

    @registry.register("r")
    def run(ctx: RoutineContext) -> RoutineResult:
        chamadas.append("routine")
        return RoutineResult(action=Action.PROCEED_TO_WEB)

    dispatch_mod.dispatch("r", _boot(), dry_run=False)
    assert chamadas == ["reset", "routine"]


def test_dispatch_propaga_dry_run() -> None:
    received: dict[str, bool] = {}

    @registry.register("r")
    def run(ctx: RoutineContext) -> RoutineResult:
        received["dry_run"] = ctx.dry_run
        return RoutineResult(action=Action.PROCEED_TO_WEB)

    dispatch_mod.dispatch("r", _boot(), dry_run=True)
    assert received["dry_run"] is True
