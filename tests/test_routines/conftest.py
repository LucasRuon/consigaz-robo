"""Fixtures dos testes em tests/test_routines/."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from intelligence.schemas import register as register_schema
from intelligence.schemas.pilot_smoke import PilotSmokeData, PilotSmokeLLM
from orchestrator import registry as routine_registry
from routines import pilot_smoke as pilot_smoke_module


@pytest.fixture(autouse=True)
def _reregister_pilot_smoke() -> Iterator[None]:
    """Re-registra schemas e rotina pilot-smoke caso outro teste tenha limpado.

    Re-registrar a mesma classe/função é no-op para schemas, e usamos `_REGISTRY`
    direto para a rotina porque o `@register` do orchestrator levanta em
    re-registro (não-idempotente). Mantém testes desacoplados.
    """
    register_schema("pilot-smoke")(PilotSmokeData)
    register_schema("pilot-smoke-llm")(PilotSmokeLLM)
    routine_registry._REGISTRY["pilot-smoke"] = pilot_smoke_module.run
    yield
