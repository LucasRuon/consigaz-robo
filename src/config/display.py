"""Serialização humana de `Settings` com `SecretStr` mascarado."""

from __future__ import annotations

from pydantic import SecretStr

from config.settings import Settings

_PREFIX_LEN = 3
_MASK = "***"
_ABSENT = "<não configurado>"


def _mask(value: SecretStr) -> str:
    raw = value.get_secret_value()
    if len(raw) <= _PREFIX_LEN:
        return _MASK
    return f"{raw[:_PREFIX_LEN]}{_MASK}"


def show(settings: Settings) -> str:
    """Retorna representação multi-linha `campo: valor` com segredos mascarados."""
    lines: list[str] = []
    for name, _field in settings.__class__.model_fields.items():
        value = getattr(settings, name)
        if isinstance(value, SecretStr):
            lines.append(f"{name}: {_mask(value)}")
        elif value is None and _is_secret_field(settings, name):
            lines.append(f"{name}: {_ABSENT}")
        else:
            lines.append(f"{name}: {value}")
    return "\n".join(lines)


def _is_secret_field(settings: Settings, name: str) -> bool:
    annotation = settings.__class__.model_fields[name].annotation
    return SecretStr in getattr(annotation, "__args__", ()) or annotation is SecretStr
