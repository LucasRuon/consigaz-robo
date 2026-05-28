"""Testes para `config.display.show`."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from config import Settings
from config.display import show


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isola do .env real e de env vars herdadas; remove keyring fake."""
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


def test_segredo_mascarado_revela_prefixo_e_oculta_resto() -> None:
    settings = Settings(
        openai_api_key=SecretStr("sk-test-123"),
        _env_file=None,  # type: ignore[call-arg]
    )
    output = show(settings)
    assert "sk-***" in output
    # valor cru NUNCA pode aparecer
    assert "sk-test-123" not in output
    assert "test-123" not in output


def test_segredo_ausente_mostra_marcador() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    output = show(settings)
    assert "openai_api_key" in output
    assert "<não configurado>" in output


def test_campo_nao_secret_mostra_valor_cru() -> None:
    settings = Settings(log_level="DEBUG", _env_file=None)  # type: ignore[call-arg]
    output = show(settings)
    assert "log_level" in output
    assert "DEBUG" in output


def test_valor_cru_jamais_aparece_em_nenhum_segredo() -> None:
    """Garante mascaramento de todos os 3 campos SecretStr conhecidos."""
    raw_values = {
        "openai_api_key": "sk-valor-super-secreto",
        "desktop_app_password": "p4ssw0rd-desktop",
        "web_platform_password": "p4ssw0rd-web",
    }
    settings = Settings(
        profile="prod",
        openai_api_key=SecretStr(raw_values["openai_api_key"]),
        desktop_app_password=SecretStr(raw_values["desktop_app_password"]),
        web_platform_password=SecretStr(raw_values["web_platform_password"]),
        _env_file=None,  # type: ignore[call-arg]
    )
    output = show(settings)
    for raw in raw_values.values():
        assert raw not in output


def test_prefixo_curto_nao_estoura() -> None:
    """SecretStr com valor mais curto que o prefixo (3) não deve quebrar."""
    settings = Settings(
        openai_api_key=SecretStr("ab"),
        _env_file=None,  # type: ignore[call-arg]
    )
    output = show(settings)
    # valor cru não aparece nem em substring
    assert " ab\n" not in output
    assert ": ab" not in output
    assert "***" in output
