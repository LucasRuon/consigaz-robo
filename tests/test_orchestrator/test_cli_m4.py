"""Testes da CLI estendida M4: --list, exit codes mapeados."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog
from pydantic import ValidationError

from config import Settings
from intelligence import llm as llm_module
from intelligence.types import Action
from orchestrator import cli, registry
from orchestrator.boot import BootContext
from orchestrator.context import RoutineContext
from orchestrator.types import RoutineResult
from platform_info import Platform, UnsupportedPlatformError


@pytest.fixture(autouse=True)
def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.chdir(tmp_path)
    for var in (
        "PROFILE",
        "LOG_LEVEL",
        "LOG_DIR",
        "OPENAI_API_KEY",
        "DESKTOP_APP_PASSWORD",
        "WEB_PLATFORM_PASSWORD",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("keyring.get_password", lambda service, key: None)
    registry._clear()
    llm_module._reset_client_for_tests()

    original_excepthook = sys.excepthook
    yield
    sys.excepthook = original_excepthook
    registry._clear()
    llm_module._reset_client_for_tests()
    root = logging.getLogger()
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)
    structlog.reset_defaults()


def _fake_boot(routine: str = "default", **kwargs: object) -> BootContext:
    return BootContext(
        platform=Platform.DARWIN,
        settings=Settings(_env_file=None),  # type: ignore[call-arg]
        routine=routine,
        log_dir=Path("logs"),
    )


def test_list_imprime_rotinas_e_sai_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    @registry.register("alpha")
    def a(ctx: RoutineContext) -> RoutineResult:
        return RoutineResult(action=Action.PROCEED_TO_WEB)

    @registry.register("zeta")
    def z(ctx: RoutineContext) -> RoutineResult:
        return RoutineResult(action=Action.PROCEED_TO_WEB)

    # Não queremos discover sobrescrever; mock para no-op.
    monkeypatch.setattr(cli.registry, "discover", lambda pkg="routines": None)
    code = cli.main(["--list"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.splitlines() == ["alpha", "zeta"]


def test_list_e_routine_sao_mutex(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["--list", "--routine", "x"])
    assert code == 2


def test_routine_inexistente_retorna_4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "boot", _fake_boot)
    monkeypatch.setattr(cli.registry, "discover", lambda pkg="routines": None)
    code = cli.main(["--routine", "nao_existe"])
    assert code == 4


def test_validation_error_em_boot_retorna_2_e_emite_boot_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(routine: str = "default", **kwargs: object) -> BootContext:
        from pydantic_core import PydanticCustomError

        raise ValidationError.from_exception_data(
            "Settings",
            [{"type": PydanticCustomError("missing", "x"), "loc": ("y",)}],
        )

    monkeypatch.setattr(cli, "boot", boom)
    code = cli.main(["--routine", "x"])
    assert code == 2
    err = capsys.readouterr().err
    payload = json.loads(err.strip().splitlines()[-1])
    assert payload["action"] == "boot_error"
    assert payload["exit_code"] == 2


def test_unsupported_platform_em_boot_retorna_3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(routine: str = "default", **kwargs: object) -> BootContext:
        raise UnsupportedPlatformError("teste")

    monkeypatch.setattr(cli, "boot", boom)
    code = cli.main(["--routine", "x"])
    assert code == 3


def test_excecao_generica_da_rotina_retorna_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "boot", _fake_boot)
    monkeypatch.setattr(cli.registry, "discover", lambda pkg="routines": None)

    @registry.register("r")
    def run(ctx: RoutineContext) -> RoutineResult:
        raise RuntimeError("falha")

    code = cli.main(["--routine", "r"])
    assert code == 1


def test_keyboard_interrupt_retorna_130(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "boot", _fake_boot)
    monkeypatch.setattr(cli.registry, "discover", lambda pkg="routines": None)

    @registry.register("r")
    def run(ctx: RoutineContext) -> RoutineResult:
        raise KeyboardInterrupt()

    code = cli.main(["--routine", "r"])
    assert code == 130


def test_dispatch_sucesso_retorna_0(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "boot", _fake_boot)
    monkeypatch.setattr(cli.registry, "discover", lambda pkg="routines": None)

    @registry.register("r")
    def run(ctx: RoutineContext) -> RoutineResult:
        return RoutineResult(action=Action.PROCEED_TO_WEB)

    assert cli.main(["--routine", "r"]) == 0


def test_dispatch_abort_retorna_5(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "boot", _fake_boot)
    monkeypatch.setattr(cli.registry, "discover", lambda pkg="routines": None)

    @registry.register("r")
    def run(ctx: RoutineContext) -> RoutineResult:
        return RoutineResult(action=Action.ABORT_IN_DESKTOP)

    assert cli.main(["--routine", "r"]) == 5


def test_help_imprime_e_sai_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["--help"])
    assert code == 0
    assert "usage:" in capsys.readouterr().out.lower()


def test_sem_args_imprime_help(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main([])
    assert code == 0
    assert "usage:" in capsys.readouterr().out.lower()
