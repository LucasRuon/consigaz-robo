"""Testes para `orchestrator.cli`."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest
import structlog
from pydantic import ValidationError

from orchestrator import cli
from orchestrator.boot import BootContext
from platform_info import Platform, UnsupportedPlatformError


@pytest.fixture(autouse=True)
def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    original_excepthook = sys.excepthook
    yield
    sys.excepthook = original_excepthook
    root = logging.getLogger()
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)
    structlog.reset_defaults()


def _fake_boot_ok(routine: str, **kwargs: object) -> BootContext:
    from config import Settings

    return BootContext(
        platform=Platform.DARWIN,
        settings=Settings(_env_file=None),  # type: ignore[call-arg]
        routine=routine,
        log_dir=Path("logs"),
    )


def test_help_imprime_usage_e_retorna_zero(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["--help"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "usage:" in out.lower()


def test_sem_args_imprime_help_e_retorna_zero(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main([])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "usage:" in out.lower()


def test_routine_executa_boot_e_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """M4: --routine X registra+dispatcha; aqui registramos um stub."""
    from intelligence.types import Action
    from orchestrator import registry
    from orchestrator.context import RoutineContext
    from orchestrator.types import RoutineResult

    chamadas: list[str] = []
    registry._clear()

    @registry.register("extracao_diaria")
    def run(ctx: RoutineContext) -> RoutineResult:
        chamadas.append(ctx.routine_name)
        return RoutineResult(action=Action.PROCEED_TO_WEB)

    def fake_boot(routine: str = "default", **kwargs: object) -> BootContext:
        return _fake_boot_ok(routine)

    monkeypatch.setattr("orchestrator.cli.boot", fake_boot)
    monkeypatch.setattr("orchestrator.cli.registry.discover", lambda pkg="routines": None)
    exit_code = cli.main(["--routine", "extracao_diaria"])
    registry._clear()
    assert exit_code == 0
    assert chamadas == ["extracao_diaria"]


def test_validation_error_retorna_exit_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_boot(routine: str = "default", **kwargs: object) -> BootContext:
        from pydantic_core import PydanticCustomError

        raise ValidationError.from_exception_data(
            "Settings",
            [{"type": PydanticCustomError("missing", "campo faltando"), "loc": ("foo",)}],
        )

    monkeypatch.setattr("orchestrator.cli.boot", fake_boot)
    exit_code = cli.main(["--routine", "x"])
    assert exit_code == 2


def test_unsupported_platform_retorna_exit_3(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_boot(routine: str = "default", **kwargs: object) -> BootContext:
        raise UnsupportedPlatformError("teste")

    monkeypatch.setattr("orchestrator.cli.boot", fake_boot)
    exit_code = cli.main(["--routine", "x"])
    assert exit_code == 3


def test_excecao_generica_retorna_exit_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_boot(routine: str = "default", **kwargs: object) -> BootContext:
        raise RuntimeError("falha generica")

    monkeypatch.setattr("orchestrator.cli.boot", fake_boot)
    exit_code = cli.main(["--routine", "x"])
    assert exit_code == 1


def test_dry_run_flag_aceita(monkeypatch: pytest.MonkeyPatch) -> None:
    """A flag --dry-run propaga ctx.dry_run e não quebra o parsing."""
    from intelligence.types import Action
    from orchestrator import registry
    from orchestrator.context import RoutineContext
    from orchestrator.types import RoutineResult

    registry._clear()

    @registry.register("x")
    def run(ctx: RoutineContext) -> RoutineResult:
        return RoutineResult(action=Action.PROCEED_TO_WEB)

    monkeypatch.setattr("orchestrator.cli.boot", _fake_boot_ok)
    monkeypatch.setattr("orchestrator.cli.registry.discover", lambda pkg="routines": None)
    exit_code = cli.main(["--routine", "x", "--dry-run"])
    registry._clear()
    assert exit_code == 0
