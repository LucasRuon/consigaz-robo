"""Modelos públicos do módulo intelligence."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Action(str, Enum):  # noqa: UP042 — mantém compat com `Action.X == "x"` em código existente
    """Decisão final do router para o orquestrador."""

    PROCEED_TO_WEB = "proceed_to_web"
    ABORT_IN_DESKTOP = "abort_in_desktop"
    RAISE_EXCEPTION = "raise_exception"


class ValidationResult(BaseModel):
    """Resultado de `validate(data, schema)`."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    is_valid: bool
    model: BaseModel | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LLMResult(BaseModel):
    """Resultado de `call_llm(...)`."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_instance: BaseModel | str
    usage_tokens_in: int
    usage_tokens_out: int
    cost_usd_estimate: float
    latency_ms: int
    prompt_name: str
    prompt_version: str
    model_used: str


class Decision(BaseModel):
    """Saída de `decide(...)`. Consumida pelo orquestrador e logger."""

    action: Action
    reason: str
    evidence: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
