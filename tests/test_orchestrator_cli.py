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


def test_routine_executa_boot_e_retorna_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[str] = []

    def fake_boot(routine: str = "default", **kwargs: object) -> BootContext:
        chamadas.append(routine)
        return _fake_boot_ok(routine)

    monkeypatch.setattr("orchestrator.cli.boot", fake_boot)
    exit_code = cli.main(["--routine", "extracao_diaria"])
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
    """A flag --dry-run não deve dar erro de parsing (é placeholder até M4)."""
    monkeypatch.setattr("orchestrator.cli.boot", _fake_boot_ok)
    exit_code = cli.main(["--routine", "x", "--dry-run"])
    assert exit_code == 0
