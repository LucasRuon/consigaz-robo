"""Schemas Pydantic da rotina `pilot-smoke` (M5).

Dois contratos:
- `PilotSmokeData`: dado extraído do desktop (operação aritmética simples).
- `PilotSmokeLLM`: resposta tipada esperada da LLM.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from intelligence.schemas import register


@register("pilot-smoke")
class PilotSmokeData(BaseModel):
    """Extração do desktop (Calculadora). Validada antes da LLM."""

    model_config = ConfigDict(extra="forbid", strict=True)

    operation: str = Field(pattern=r"^\d+\s*[+\-*/]\s*\d+$")
    result: int
    observation: str = Field(min_length=1, max_length=500)


@register("pilot-smoke-llm")
class PilotSmokeLLM(BaseModel):
    """Resposta tipada da LLM consumida por `router.decide`."""

    model_config = ConfigDict(extra="forbid", strict=True)

    decision: Literal["approve", "reject", "escalate"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=200)


__all__ = ["PilotSmokeData", "PilotSmokeLLM"]
