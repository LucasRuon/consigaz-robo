"""Validação determinística via Pydantic."""

from __future__ import annotations

from typing import Any

import pydantic
from pydantic import BaseModel

from intelligence.exceptions import ValidationCodeError
from intelligence.types import ValidationResult


def validate(
    data: dict[str, Any] | None,
    schema: type[BaseModel],
) -> ValidationResult:
    """Valida `data` contra `schema`. Não lança em erro de dado.

    Lança `ValidationCodeError` se o validador customizado falhar com
    exceção diferente de `pydantic.ValidationError` (bug de código).
    """
    if data is None:
        return ValidationResult(is_valid=False, errors=["payload vazio"])
    try:
        instance = schema.model_validate(data)
    except pydantic.ValidationError as e:
        errors = [
            f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
            for err in e.errors()
        ]
        return ValidationResult(is_valid=False, errors=errors)
    except Exception as e:
        raise ValidationCodeError(
            schema=schema.__name__, original_exception=e
        ) from e
    return ValidationResult(is_valid=True, model=instance)
