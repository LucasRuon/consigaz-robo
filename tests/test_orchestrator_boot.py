"""Testes para `orchestrator.boot`."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest
import structlog
from pydantic import ValidationError

from orchestrator.boot import BootContext, boot
from platform_info import Platform, UnsupportedPlatformError


@pytest.fixture(autouse=True)
def _clean_env_and_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Limpa env vars, isola .env, neutraliza keyring, reseta logger e excepthook."""
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
    monkeypatch.setattr("pyautogui.screenshot", lambda *a, **k: None)

    original_excepthook = sys.excepthook
    yield
    sys.excepthook = original_excepthook
    root = logging.getLogger()
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)
    structlog.reset_defaults()


def test_boot_dev_sem_segredos_retorna_context(tmp_path: Path) -> None:
    ctx = boot("default", log_dir=tmp_path / "logs", errors_dir=tmp_path / "errors")
    assert isinstance(ctx, BootContext)
    assert ctx.routine == "default"
    assert ctx.platform in {Platform.DARWIN, Platform.WIN32}
    assert ctx.settings.profile == "dev"
    assert ctx.log_dir == tmp_path / "logs"


def test_boot_prod_sem_segredos_lanca_validation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROFILE", "prod")
    with pytest.raises(ValidationError) as excinfo:
        boot("r", log_dir=tmp_path / "logs", errors_dir=tmp_path / "errors")
    assert "openai_api_key" in str(excinfo.value)


def test_boot_plataforma_nao_suportada_lanca(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("orchestrator.boot.current_platform", _raise_unsupported)
    with pytest.raises(UnsupportedPlatformError):
        boot("r", log_dir=tmp_path / "logs", errors_dir=tmp_path / "errors")


def test_boot_inicializa_logger_em_disco(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    boot("rotina_xyz", log_dir=log_dir, errors_dir=tmp_path / "errors")
    arquivos = list(log_dir.glob("*_rotina_xyz.*"))
    sufixos = sorted(p.suffix for p in arquivos)
    assert sufixos == [".json", ".log"]


def test_boot_instala_excepthook(tmp_path: Path) -> None:
    excepthook_antes = sys.excepthook
    boot("r", log_dir=tmp_path / "logs", errors_dir=tmp_path / "errors")
    assert sys.excepthook is not excepthook_antes


def _raise_unsupported() -> Platform:
    raise UnsupportedPlatformError("test")
