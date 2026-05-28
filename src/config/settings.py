"""Configuração da aplicação carregada de `.env` e variáveis de ambiente."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from config.keyring_source import KeyringSettingsSource

DEFAULT_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "cpf",
        "cnpj",
        "rg",
    }
)


_REQUIRED_PROD_SECRETS: tuple[str, ...] = (
    "openai_api_key",
    "desktop_app_password",
    "web_platform_password",
)


class Settings(BaseSettings):
    """Configuração tipada do robô RPA."""

    profile: Literal["dev", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_dir: Path = Path("logs")

    openai_api_key: SecretStr | None = None
    desktop_app_password: SecretStr | None = None
    web_platform_password: SecretStr | None = None

    web_headless: bool = False
    web_login_url_patterns: list[str] = ["/login", "/auth", "/signin", "/entrar"]
    web_default_timeout: float = 15.0
    web_navigate_timeout: float = 30.0
    web_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    web_viewport_width: int = 1280
    web_viewport_height: int = 800
    web_locale: str = "pt-BR"

    sensitive_keys: frozenset[str] = DEFAULT_SENSITIVE_KEYS

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def _require_secrets_in_prod(self) -> Settings:
        """Em `profile=prod`, exige segredos obrigatórios sem vazar valores."""
        if self.profile != "prod":
            return self

        missing = [name for name in _REQUIRED_PROD_SECRETS if getattr(self, name) is None]
        if missing:
            raise ValueError(
                "Segredos obrigatórios ausentes em profile=prod: " + ", ".join(missing)
            )
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Precedência: init > keyring > env > .env > file secrets."""
        return (
            init_settings,
            KeyringSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )
