"""Configuração da aplicação carregada de `.env` e variáveis de ambiente."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
