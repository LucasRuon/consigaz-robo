"""Testes dos schemas `pilot-smoke` e `pilot-smoke-llm`."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from intelligence.schemas import get_schema
from intelligence.schemas.pilot_smoke import PilotSmokeData, PilotSmokeLLM


def test_schemas_registered() -> None:
    assert get_schema("pilot-smoke") is PilotSmokeData
    assert get_schema("pilot-smoke-llm") is PilotSmokeLLM


def test_pilot_smoke_data_valid() -> None:
    data = PilotSmokeData(
        operation="2 + 3",
        result=5,
        observation="cálculo de teste end-to-end",
    )
    assert data.operation == "2 + 3"
    assert data.result == 5


def test_pilot_smoke_data_rejects_non_numeric_operation() -> None:
    with pytest.raises(ValidationError):
        PilotSmokeData(operation="abc", result=5, observation="x")


def test_pilot_smoke_llm_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        PilotSmokeLLM(decision="approve", confidence=1.5, summary="ok")
