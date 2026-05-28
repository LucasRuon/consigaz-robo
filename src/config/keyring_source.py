"""Custom source para pydantic-settings que lê segredos do keyring nativo do SO."""
from __future__ import annotations

from typing import Any

import keyring
from keyring.errors import KeyringError
from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

KEYRING_SERVICE = "consigaz-robo"


class KeyringSettingsSource(PydanticBaseSettingsSource):
    """Source que resolve cada field via ``keyring.get_password(KEYRING_SERVICE, field_name)``.

    - Se o backend de keyring lançar ``KeyringError``, retorna ``{}`` silenciosamente
      para que outros sources (env, .env) assumam.
    - Se uma chave não existir no keyring, simplesmente não inclui no dict.
    - Demais exceções são propagadas (bug real).
    """

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        value = keyring.get_password(KEYRING_SERVICE, field_name)
        return value, field_name, False

    def __call__(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field_name, field in self.settings_cls.model_fields.items():
            try:
                value, key, _ = self.get_field_value(field, field_name)
            except KeyringError:
                return {}
            if value is not None:
                result[key] = value
        return result
