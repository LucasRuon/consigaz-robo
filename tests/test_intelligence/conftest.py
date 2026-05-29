"""Fixtures dos testes em tests/test_intelligence/."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from intelligence.schemas import register
from intelligence.schemas.pilot_smoke import PilotSmokeData, PilotSmokeLLM


@pytest.fixture(autouse=True)
def _reregister_pilot_smoke_schemas() -> Iterator[None]:
    """Re-registra schemas pilot-smoke caso outro teste tenha limpado o registry.

    Re-registrar a MESMA classe é no-op (ver test_re_register_same_class_is_noop),
    então o overhead é desprezível e remove o acoplamento entre testes.
    """
    register("pilot-smoke")(PilotSmokeData)
    register("pilot-smoke-llm")(PilotSmokeLLM)
    yield
