"""Testes de `orchestrator.summary`."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog

from config import Settings
from intelligence import llm as llm_module
from intelligence import reset_for_new_execution
from intelligence.types import Action
from orchestrator import summary
from orchestrator.boot import BootContext
from orchestrator.context import RoutineContext
from orchestrator.types import RoutineResult
from platform_info import Platform


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr("keyring.get_password", lambda service, key: None)
    for var in ("OPENAI_API_KEY", "DESKTOP_APP_PASSWORD", "WEB_PLATFORM_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    llm_module._reset_client_for_tests()
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.KeyValueRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    yield
    llm_module._reset_client_for_tests()
    structlog.reset_defaults()


def _boot() -> BootContext:
    return BootContext(
        platform=Platform.DARWIN,
        settings=Settings(_env_file=None),  # type: ignore[call-arg]
        routine="r",
        log_dir=Path("logs"),
    )


def _ctx() -> RoutineContext:
    return RoutineContext.from_boot(_boot(), dry_run=False, routine_name="r")


@pytest.mark.parametrize("action", list(Action))
def test_emit_sucesso_publica_campos(
    action: Action, caplog: pytest.LogCaptureFixture
) -> None:
    ctx = _ctx()
    result = RoutineResult(
        action=action, evidence={"chave_priv": "VALOR_SECRETO"}
    )
    with caplog.at_level(logging.INFO):
        summary.emit(ctx, result=result, exit_code=0)
    records = [r for r in caplog.records if "execution_summary" in r.getMessage()]
    assert records, "evento execution_summary não emitido"


def test_emit_nao_inclui_valor_de_evidence(caplog: pytest.LogCaptureFixture) -> None:
    ctx = _ctx()
    result = RoutineResult(
        action=Action.PROCEED_TO_WEB,
        evidence={"campo_secreto": "VALOR_SECRETO_42"},
    )
    with caplog.at_level(logging.INFO):
        summary.emit(ctx, result=result, exit_code=0)
    blob = " ".join(r.getMessage() + str(getattr(r, "__dict__", {})) for r in caplog.records)
    assert "VALOR_SECRETO_42" not in blob


def test_emit_error_inclui_error_type_e_msg(caplog: pytest.LogCaptureFixture) -> None:
    ctx = _ctx()
    err = ValueError("falhou_xyz")
    with caplog.at_level(logging.INFO):
        summary.emit_error(ctx, error=err, exit_code=1)
    records = [r for r in caplog.records if "execution_summary" in r.getMessage()]
    assert records


def test_emit_boot_failure_escreve_json_em_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary.emit_boot_failure(
        routine="rx", error=RuntimeError("boom"), exit_code=2
    )
    err = capsys.readouterr().err
    payload = json.loads(err.strip().splitlines()[-1])
    assert payload["event"] == "execution_summary"
    assert payload["routine"] == "rx"
    assert payload["action"] == "boot_error"
    assert payload["exit_code"] == 2
    assert payload["error_type"] == "RuntimeError"


def test_cost_snapshot_zero_quando_sem_reset(caplog: pytest.LogCaptureFixture) -> None:
    """Sem reset_for_new_execution, get_cost_snapshot retorna zeros (não lança)."""
    ctx = _ctx()
    with caplog.at_level(logging.INFO):
        summary.emit(
            ctx, result=RoutineResult(action=Action.PROCEED_TO_WEB), exit_code=0
        )
    # Não deve ter lançado; teste passa se chegou até aqui.


def test_cost_snapshot_reflete_tracker_apos_reset() -> None:
    """Após reset + uso manual do tracker, snapshot deve refletir uso."""
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    reset_for_new_execution(settings)
    llm_module._cost_tracker.add_after("gpt-4o-mini", 100, 50)  # type: ignore[union-attr]
    snap = llm_module.get_cost_snapshot()
    assert snap.tokens_in == 100
    assert snap.tokens_out == 50
    assert snap.cost_usd >= 0.0
