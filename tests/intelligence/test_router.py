"""Testes de intelligence.router.decide()."""

from __future__ import annotations

import copy
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import BaseModel

from intelligence.exceptions import RouterContractError
from intelligence.router import decide
from intelligence.types import Action, LLMResult, ValidationResult


class _LLMDecision(BaseModel):
    decision: str
    confidence: float = 1.0
    reason: str = "ok"


def _llm(decision: str, confidence: float = 1.0, reason: str = "ok") -> LLMResult:
    return LLMResult(
        model_instance=_LLMDecision(
            decision=decision, confidence=confidence, reason=reason
        ),
        usage_tokens_in=10,
        usage_tokens_out=5,
        cost_usd_estimate=0.001,
        latency_ms=50,
        prompt_name="t",
        prompt_version="1.0",
        model_used="gpt-4o-mini",
    )


# ── Regra 1: validation inválida ─────────────────────────────────────────


def test_invalid_validation_returns_abort() -> None:
    v = ValidationResult(is_valid=False, errors=["campo X faltando"])
    d = decide(v)
    assert d.action == Action.ABORT_IN_DESKTOP
    assert d.confidence == 1.0
    assert d.evidence == {"errors": ["campo X faltando"]}


def test_invalid_validation_ignores_llm_result() -> None:
    v = ValidationResult(is_valid=False, errors=["x"])
    d = decide(v, _llm("approve"))
    assert d.action == Action.ABORT_IN_DESKTOP


# ── Regra 2: validation ok + sem LLM ─────────────────────────────────────


def test_valid_no_llm_returns_proceed() -> None:
    class M(BaseModel):
        x: int

    v = ValidationResult(is_valid=True, model=M(x=1))
    d = decide(v)
    assert d.action == Action.PROCEED_TO_WEB
    assert d.confidence == 1.0
    assert d.evidence["model"] == {"x": 1}


def test_valid_no_llm_no_model_returns_proceed_empty_evidence() -> None:
    v = ValidationResult(is_valid=True, model=None)
    d = decide(v)
    assert d.action == Action.PROCEED_TO_WEB
    assert d.evidence == {"model": {}}


# ── Regra 3/5: mapeamento approve/reject/escalate ────────────────────────


@pytest.mark.parametrize(
    "decision,expected",
    [
        ("approve", Action.PROCEED_TO_WEB),
        ("reject", Action.ABORT_IN_DESKTOP),
        ("escalate", Action.RAISE_EXCEPTION),
    ],
)
def test_llm_decision_mapping(decision: str, expected: Action) -> None:
    v = ValidationResult(is_valid=True)
    d = decide(v, _llm(decision, confidence=0.9))
    assert d.action == expected


def test_llm_decision_unknown_value_raises_contract_error() -> None:
    v = ValidationResult(is_valid=True)
    with pytest.raises(RouterContractError):
        decide(v, _llm("indecisão", confidence=0.9))


# ── Regra 4: confidence threshold ────────────────────────────────────────


def test_low_confidence_forces_raise_exception() -> None:
    v = ValidationResult(is_valid=True)
    d = decide(v, _llm("approve", confidence=0.5))
    assert d.action == Action.RAISE_EXCEPTION
    assert "abaixo" in d.reason
    assert d.confidence == 0.5


def test_custom_min_confidence_respected() -> None:
    v = ValidationResult(is_valid=True)
    d = decide(v, _llm("approve", confidence=0.5), min_confidence=0.3)
    assert d.action == Action.PROCEED_TO_WEB


def test_confidence_exactly_at_threshold_passes() -> None:
    v = ValidationResult(is_valid=True)
    d = decide(v, _llm("approve", confidence=0.7), min_confidence=0.7)
    assert d.action == Action.PROCEED_TO_WEB


# ── Regra 3: contrato (sem .decision) ────────────────────────────────────


def test_llm_without_decision_raises_contract_error() -> None:
    class _NoDecision(BaseModel):
        x: int

    bad = LLMResult(
        model_instance=_NoDecision(x=1),
        usage_tokens_in=1,
        usage_tokens_out=1,
        cost_usd_estimate=0.0,
        latency_ms=1,
        prompt_name="t",
        prompt_version="1.0",
        model_used="x",
    )
    v = ValidationResult(is_valid=True)
    with pytest.raises(RouterContractError) as exc:
        decide(v, bad)
    assert exc.value.expected_field == "decision"


def test_llm_string_response_raises_contract_error() -> None:
    bad = LLMResult(
        model_instance="texto livre sem decision",
        usage_tokens_in=1,
        usage_tokens_out=1,
        cost_usd_estimate=0.0,
        latency_ms=1,
        prompt_name="t",
        prompt_version="1.0",
        model_used="x",
    )
    v = ValidationResult(is_valid=True)
    with pytest.raises(RouterContractError):
        decide(v, bad)


def test_llm_decision_without_confidence_assumes_one() -> None:
    class _OnlyDecision(BaseModel):
        decision: str

    r = LLMResult(
        model_instance=_OnlyDecision(decision="approve"),
        usage_tokens_in=1,
        usage_tokens_out=1,
        cost_usd_estimate=0.0,
        latency_ms=1,
        prompt_name="t",
        prompt_version="1.0",
        model_used="x",
    )
    v = ValidationResult(is_valid=True)
    d = decide(v, r)
    assert d.action == Action.PROCEED_TO_WEB
    assert d.confidence == 1.0


# ── Pureza ────────────────────────────────────────────────────────────────


def test_decide_is_deterministic() -> None:
    v = ValidationResult(is_valid=True)
    llm = _llm("approve", confidence=0.9)
    first = decide(v, llm).model_dump(mode="json")
    for _ in range(99):
        assert decide(v, llm).model_dump(mode="json") == first


def test_decide_does_not_mutate_inputs() -> None:
    v = ValidationResult(is_valid=True, errors=["a"], warnings=["w"])
    llm = _llm("approve", confidence=0.9)
    v_before = v.model_dump()
    llm_before = llm.model_dump()
    decide(v, llm)
    assert v.model_dump() == v_before
    assert llm.model_dump() == llm_before


def test_decide_does_not_mutate_invalid_errors() -> None:
    errs = ["a", "b"]
    v = ValidationResult(is_valid=False, errors=errs)
    d = decide(v)
    d.evidence["errors"].append("c")  # type: ignore[union-attr]
    assert errs == ["a", "b"]  # original intacta


# ── Serialização JSON segura ────────────────────────────────────────────


def test_decision_with_decimal_evidence_serializes() -> None:
    class _D(BaseModel):
        decision: str
        confidence: float
        valor: Decimal
        quando: datetime

    inst = _D(
        decision="approve",
        confidence=0.9,
        valor=Decimal("1.50"),
        quando=datetime(2026, 1, 1),
    )
    r = LLMResult(
        model_instance=inst,
        usage_tokens_in=1,
        usage_tokens_out=1,
        cost_usd_estimate=0.0,
        latency_ms=1,
        prompt_name="t",
        prompt_version="1.0",
        model_used="x",
    )
    v = ValidationResult(is_valid=True)
    d = decide(v, r)
    dumped: dict[str, Any] = d.model_dump(mode="json")
    import json

    json.dumps(dumped)  # não lança


def test_evidence_includes_llm_dump() -> None:
    v = ValidationResult(is_valid=True)
    d = decide(v, _llm("approve", confidence=0.9, reason="motivo X"))
    assert "llm" in d.evidence
    assert d.evidence["llm"]["decision"] == "approve"


def test_reason_comes_from_llm_when_available() -> None:
    v = ValidationResult(is_valid=True)
    d = decide(v, _llm("approve", confidence=0.9, reason="motivo X"))
    assert d.reason == "motivo X"
