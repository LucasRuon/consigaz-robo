"""Roteador de decisão: função pura validation + llm_result → Decision."""

from __future__ import annotations

from intelligence.exceptions import RouterContractError
from intelligence.types import Action, Decision, LLMResult, ValidationResult

_ACTION_MAP: dict[str, Action] = {
    "approve": Action.PROCEED_TO_WEB,
    "reject": Action.ABORT_IN_DESKTOP,
    "escalate": Action.RAISE_EXCEPTION,
}


def decide(
    validation: ValidationResult,
    llm_result: LLMResult | None = None,
    *,
    min_confidence: float = 0.7,
) -> Decision:
    """Decide próxima ação. Função pura — sem I/O, sem logging, sem mutação.

    Regras:
        1. validation inválida → ABORT_IN_DESKTOP
        2. validation ok + sem LLM → PROCEED_TO_WEB
        3. LLM result sem `.decision` → RouterContractError
        4. confidence < min_confidence → RAISE_EXCEPTION
        5. mapeia decision ∈ {approve, reject, escalate} → Action
    """
    if not validation.is_valid:
        return Decision(
            action=Action.ABORT_IN_DESKTOP,
            reason="dados inválidos",
            evidence={"errors": list(validation.errors)},
            confidence=1.0,
        )

    if llm_result is None:
        model_dump = (
            validation.model.model_dump(mode="json") if validation.model else {}
        )
        return Decision(
            action=Action.PROCEED_TO_WEB,
            reason="validação ok, sem análise LLM necessária",
            evidence={"model": model_dump},
            confidence=1.0,
        )

    instance = llm_result.model_instance
    if not hasattr(instance, "decision"):
        raise RouterContractError(
            expected_field="decision",
            got_type=type(instance).__name__,
        )

    confidence = float(getattr(instance, "confidence", 1.0))
    decision_str = str(getattr(instance, "decision"))

    if confidence < min_confidence:
        return Decision(
            action=Action.RAISE_EXCEPTION,
            reason=(
                f"confiança {confidence:.2f} abaixo do mínimo {min_confidence:.2f}"
            ),
            evidence={"llm": _dump(instance)},
            confidence=confidence,
        )

    if decision_str not in _ACTION_MAP:
        raise RouterContractError(
            expected_field=f"decision in {sorted(_ACTION_MAP)}",
            got_type=f"value={decision_str!r}",
        )

    reason = str(getattr(instance, "reason", "decisão da LLM"))
    return Decision(
        action=_ACTION_MAP[decision_str],
        reason=reason,
        evidence={"llm": _dump(instance)},
        confidence=confidence,
    )


def _dump(instance: object) -> dict[str, object] | str:
    dump = getattr(instance, "model_dump", None)
    if callable(dump):
        try:
            return dump(mode="json")  # type: ignore[no-any-return]
        except TypeError:
            return dump()  # type: ignore[no-any-return]
    return str(instance)
