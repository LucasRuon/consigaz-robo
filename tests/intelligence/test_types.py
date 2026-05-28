"""Testes dos tipos públicos."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from intelligence.types import Action, Decision, LLMResult, ValidationResult


def test_action_is_str_enum() -> None:
    assert Action.PROCEED_TO_WEB == "proceed_to_web"
    assert Action.ABORT_IN_DESKTOP == "abort_in_desktop"
    assert Action.RAISE_EXCEPTION == "raise_exception"


def test_validation_result_defaults() -> None:
    r = ValidationResult(is_valid=True)
    assert r.errors == []
    assert r.warnings == []
    assert r.model is None


def test_validation_result_with_model() -> None:
    class Foo(BaseModel):
        x: int

    r = ValidationResult(is_valid=True, model=Foo(x=1))
    assert isinstance(r.model, Foo)


def test_llm_result_basic() -> None:
    r = LLMResult(
        model_instance="texto livre",
        usage_tokens_in=10,
        usage_tokens_out=20,
        cost_usd_estimate=0.001,
        latency_ms=120,
        prompt_name="x",
        prompt_version="1.0.0",
        model_used="gpt-4o-mini",
    )
    assert r.model_instance == "texto livre"


def test_decision_confidence_in_range() -> None:
    d = Decision(action=Action.PROCEED_TO_WEB, reason="ok", evidence={}, confidence=0.5)
    assert d.confidence == 0.5


def test_decision_confidence_rejects_negative() -> None:
    with pytest.raises(ValidationError):
        Decision(action=Action.PROCEED_TO_WEB, reason="x", evidence={}, confidence=-0.1)


def test_decision_confidence_rejects_above_one() -> None:
    with pytest.raises(ValidationError):
        Decision(action=Action.PROCEED_TO_WEB, reason="x", evidence={}, confidence=1.5)


def test_decision_dump_json_serializes_decimal_and_datetime() -> None:
    d = Decision(
        action=Action.PROCEED_TO_WEB,
        reason="ok",
        evidence={"valor": Decimal("1.50"), "quando": datetime(2026, 1, 1, 12, 0, 0)},
        confidence=0.9,
    )
    dumped = d.model_dump(mode="json")
    payload = json.dumps(dumped)
    assert '"valor"' in payload
    assert '"quando"' in payload
    assert "2026-01-01" in payload


def test_decision_action_serialized_as_string() -> None:
    d = Decision(action=Action.ABORT_IN_DESKTOP, reason="x", evidence={}, confidence=1.0)
    assert d.model_dump(mode="json")["action"] == "abort_in_desktop"
