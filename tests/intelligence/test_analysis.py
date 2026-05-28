"""Testes de intelligence.analysis."""

from __future__ import annotations

import subprocess
import sys
from decimal import Decimal

import pandas as pd
import pytest

from intelligence.analysis import compare_against_history, validate_range


def test_validate_range_inside_returns_none() -> None:
    assert validate_range(5, 0, 10) is None


def test_validate_range_below_lower() -> None:
    msg = validate_range(-1, 0, 10)
    assert msg is not None
    assert "menor que mínimo" in msg


def test_validate_range_above_upper() -> None:
    msg = validate_range(11, 0, 10)
    assert msg is not None
    assert "maior que máximo" in msg


def test_validate_range_custom_field_name() -> None:
    msg = validate_range(-1, 0, 10, field_name="preco")
    assert msg is not None
    assert "preco" in msg


def test_validate_range_accepts_decimal() -> None:
    assert validate_range(Decimal("5.5"), Decimal("0"), Decimal("10")) is None


def test_compare_empty_series_returns_true() -> None:
    assert compare_against_history(5.0, pd.Series([], dtype=float)) is True


def test_compare_single_element_equal_returns_true() -> None:
    assert compare_against_history(5.0, pd.Series([5.0])) is True


def test_compare_single_element_not_equal_returns_false() -> None:
    assert compare_against_history(6.0, pd.Series([5.0])) is False


def test_compare_within_threshold() -> None:
    s = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
    assert compare_against_history(13.0, s, threshold_std=2.0) is True


def test_compare_outside_threshold() -> None:
    s = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0])
    # std=0 → exige igualdade
    assert compare_against_history(11.0, s) is False


def test_compare_accepts_decimal_value() -> None:
    s = pd.Series([10.0, 12.0, 14.0])
    assert compare_against_history(Decimal("12"), s) is True


def test_validation_module_does_not_import_pandas() -> None:
    """Carregar `intelligence.validation` sozinho não deve trazer pandas."""
    code = (
        "import sys\n"
        "import intelligence.validation  # noqa: F401\n"
        "print('pandas' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "False", (
        f"pandas vazou no import de intelligence.validation: "
        f"stdout={result.stdout!r}"
    )


def test_analysis_module_top_level_does_not_import_pandas() -> None:
    """Importar `intelligence.analysis` sem chamar funções não deve trazer pandas."""
    code = (
        "import sys\n"
        "import intelligence.analysis  # noqa: F401\n"
        "print('pandas' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    # TYPE_CHECKING guard mantém pandas fora do top-level
    assert result.stdout.strip() == "False"
