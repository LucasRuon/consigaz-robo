"""Helpers de análise agregada (Pandas opcional, lazy import)."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def validate_range(
    value: float | Decimal,
    lo: float | Decimal,
    hi: float | Decimal,
    field_name: str = "valor",
) -> str | None:
    """Retorna string de erro se `value` fora de `[lo, hi]`; `None` se ok."""
    if value < lo:
        return f"{field_name} ({value}) menor que mínimo ({lo})"
    if value > hi:
        return f"{field_name} ({value}) maior que máximo ({hi})"
    return None


def compare_against_history(
    value: float | Decimal,
    series: pd.Series,
    threshold_std: float = 2.0,
) -> bool:
    """True se `value` está dentro de `threshold_std` desvios da média de `series`.

    Série vazia → True (sem base para reprovar). Série de 1 elemento (std=0)
    → exige igualdade exata.
    """
    if len(series) == 0:
        return True
    value_f = float(value)
    mean = float(series.mean())
    if len(series) == 1:
        return value_f == mean
    std = float(series.std())
    if std == 0:
        return value_f == mean
    return abs(value_f - mean) <= threshold_std * std
