"""Testes para `config.settings.Settings`."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from config import DEFAULT_SENSITIVE_KEYS, Settings


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isola os testes do `.env` do projeto e de variáveis de ambiente herdadas."""
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


def test_dev_profile_sem_segredos_ok() -> None:
    settings = Settings(profile="dev", _env_file=None)  # type: ignore[call-arg]
    assert settings.profile == "dev"
    assert settings.openai_api_key is None
    assert settings.desktop_app_password is None
    assert settings.web_platform_password is None
    assert settings.sensitive_keys == DEFAULT_SENSITIVE_KEYS


def test_prod_profile_sem_segredos_falha_com_nomes_dos_campos() -> None:
    with pytest.raises(ValidationError) as excinfo:
        Settings(profile="prod", _env_file=None)  # type: ignore[call-arg]

    message = str(excinfo.value)
    assert "openai_api_key" in message
    assert "desktop_app_password" in message
    assert "web_platform_password" in message


def test_prod_profile_com_todos_segredos_ok() -> None:
    settings = Settings(
        profile="prod",
        openai_api_key=SecretStr("sk-x"),
        desktop_app_password=SecretStr("a"),
        web_platform_password=SecretStr("b"),
        _env_file=None,  # type: ignore[call-arg]
    )
    assert settings.profile == "prod"
    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "sk-x"
    assert settings.desktop_app_password is not None
    assert settings.desktop_app_password.get_secret_value() == "a"
    assert settings.web_platform_password is not None
    assert settings.web_platform_password.get_secret_value() == "b"


def test_carrega_valores_de_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "PROFILE=dev\n"
        "LOG_LEVEL=WARNING\n"
        "OPENAI_API_KEY=sk-from-env\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings()
    assert settings.profile == "dev"
    assert settings.log_level == "WARNING"
    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "sk-from-env"


def test_variavel_de_ambiente_sobrescreve_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.log_level == "DEBUG"


def test_extra_forbid_rejeita_campo_desconhecido() -> None:
    with pytest.raises(ValidationError):
        Settings(unknown_field="x", _env_file=None)  # type: ignore[call-arg]


def test_prod_profile_falha_lista_apenas_segredos_ausentes() -> None:
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            profile="prod",
            openai_api_key=SecretStr("sk-x"),
            _env_file=None,  # type: ignore[call-arg]
        )

    message = str(excinfo.value)
    assert "desktop_app_password" in message
    assert "web_platform_password" in message
    # openai_api_key foi fornecido; não deve aparecer como faltante
    assert "openai_api_key" not in message


def test_log_dir_default_e_path() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert isinstance(settings.log_dir, Path)
    assert settings.log_dir == Path("logs")


def test_validador_nao_vaza_valor_do_segredo() -> None:
    """Mensagem de erro não deve conter o valor real do segredo, apenas nomes."""
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            profile="prod",
            openai_api_key=SecretStr("sk-super-secret-value-123"),
            _env_file=None,  # type: ignore[call-arg]
        )

    message = str(excinfo.value)
    assert "sk-super-secret-value-123" not in message
