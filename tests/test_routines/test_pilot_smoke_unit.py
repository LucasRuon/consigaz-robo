"""Testes unitários da rotina `pilot-smoke` (sem Calculadora real, sem OpenAI)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
import structlog
from pydantic import SecretStr

from config import Settings
from intelligence import (
    Action,
    LLMResult,
)
from intelligence.schemas.pilot_smoke import PilotSmokeLLM
from orchestrator import registry as registry_module
from orchestrator.context import RoutineContext
from platform_info import Platform
from routines import pilot_smoke as ps


def _make_ctx(*, dry_run: bool = False) -> RoutineContext:
    settings = Settings(openai_api_key=SecretStr("test-key"))
    logger = structlog.get_logger("test")
    return RoutineContext(
        platform=Platform.DARWIN,
        settings=settings,
        logger=logger,
        routine_name="pilot-smoke",
        dry_run=dry_run,
        started_at=datetime.now(tz=UTC),
    )


def _make_llm(decision: str, confidence: float) -> LLMResult:
    return LLMResult(
        model_instance=PilotSmokeLLM(
            decision=decision,  # type: ignore[arg-type]
            confidence=confidence,
            summary="resumo de teste",
        ),
        usage_tokens_in=10,
        usage_tokens_out=5,
        cost_usd_estimate=0.0001,
        latency_ms=50,
        prompt_name="pilot-smoke",
        prompt_version="1",
        model_used="gpt-4o-mini",
    )


@pytest.fixture
def mock_pipeline(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patcha desktop + web + LLM e retorna registros do que foi chamado."""
    calls: list[str] = []

    def fake_extract(ctx: RoutineContext) -> dict[str, Any]:
        calls.append("extract")
        return {
            "operation": "2 + 3",
            "result": 5,
            "observation": "cálculo de teste end-to-end",
        }

    def fake_call_llm(
        prompt_name: str,
        params: dict[str, Any],
        response_model: type,
        settings: Settings,
    ) -> LLMResult:
        calls.append("llm")
        return _make_llm("approve", 0.95)

    def fake_submit(ctx: RoutineContext, validation: Any, llm: Any) -> dict[str, Any]:
        calls.append("web")
        return {"final_url": "https://httpbin.org/post", "status": 200}

    monkeypatch.setattr(ps, "_extract_from_calculator", fake_extract)
    monkeypatch.setattr(ps, "call_llm", fake_call_llm)
    monkeypatch.setattr(ps, "_submit_to_httpbin", fake_submit)

    return {"calls": calls}


def test_run_invokes_pipeline_in_order(mock_pipeline: dict[str, Any]) -> None:
    ctx = _make_ctx()
    result = ps.run(ctx)
    assert mock_pipeline["calls"] == ["extract", "llm", "web"]
    assert result.action is Action.PROCEED_TO_WEB


def test_dry_run_skips_web_submit(mock_pipeline: dict[str, Any]) -> None:
    ctx = _make_ctx(dry_run=True)
    result = ps.run(ctx)
    assert "web" not in mock_pipeline["calls"]
    assert result.evidence["dry_run"] is True
    assert "web_final_url" not in result.evidence
    assert "web_status" not in result.evidence


def test_evidence_keys_are_safe(mock_pipeline: dict[str, Any]) -> None:
    ctx = _make_ctx()
    result = ps.run(ctx)
    for key in result.evidence:
        assert not key.startswith("_"), f"chave privada em evidence: {key}"
    forbidden_substrings = ("password", "secret", "api_key", "token")
    payload = repr(result.evidence).lower()
    for needle in forbidden_substrings:
        assert needle not in payload, f"evidence vazou {needle!r}"


def test_low_confidence_raises_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_extract(ctx: RoutineContext) -> dict[str, Any]:
        return {
            "operation": "2 + 3",
            "result": 5,
            "observation": "cálculo de teste end-to-end",
        }

    def fake_call_llm(*args: Any, **kwargs: Any) -> LLMResult:
        return _make_llm("approve", 0.5)

    web_called = []

    def fake_submit(*args: Any, **kwargs: Any) -> dict[str, Any]:
        web_called.append(True)
        return {}

    monkeypatch.setattr(ps, "_extract_from_calculator", fake_extract)
    monkeypatch.setattr(ps, "call_llm", fake_call_llm)
    monkeypatch.setattr(ps, "_submit_to_httpbin", fake_submit)

    ctx = _make_ctx()
    result = ps.run(ctx)
    assert result.action is Action.RAISE_EXCEPTION
    assert not web_called


def test_validation_failure_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_extract(ctx: RoutineContext) -> dict[str, Any]:
        return {"operation": "invalido", "result": 5, "observation": "x"}

    llm_called = []

    def fake_call_llm(*args: Any, **kwargs: Any) -> LLMResult:
        llm_called.append(True)
        return _make_llm("approve", 0.95)

    monkeypatch.setattr(ps, "_extract_from_calculator", fake_extract)
    monkeypatch.setattr(ps, "call_llm", fake_call_llm)

    ctx = _make_ctx()
    result = ps.run(ctx)
    assert result.action is Action.ABORT_IN_DESKTOP
    assert not llm_called, "LLM não deveria ser chamada quando validação falha"


def test_registered_with_correct_name() -> None:
    registry_module.discover("routines")
    assert registry_module.get("pilot-smoke") is ps.run


def test_submit_strips_login_selectors_before_open_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`open_browser` não pode receber o bloco `login`, senão o session-check
    procura `#app-main` em `about:blank` e dispara LoginRequiredError indevido."""
    from intelligence import validate
    from intelligence.schemas.pilot_smoke import PilotSmokeData

    captured: dict[str, Any] = {}

    def fake_load_selectors() -> dict[str, dict[str, str]]:
        return {
            "login": {"_session_sentinel": "#app-main", "submit": "x"},
            "pilot_smoke": {
                "_session_sentinel": "input[name='custname']",
                "custname": "input[name='custname']",
                "custtel": "input[name='custtel']",
                "custemail": "input[name='custemail']",
                "comments": "textarea[name='comments']",
                "submit": "form button",
            },
        }

    class FakePage:
        url = "https://httpbin.org/post"

        def locator(self, _: str) -> Any:
            class _Loc:
                first = type("_F", (), {"click": lambda self: None})()

            return _Loc()

        def expect_navigation(self, **_: Any) -> Any:
            class _Ctx:
                def __enter__(self_inner) -> None: return None
                def __exit__(self_inner, *a: Any) -> None: return None

            return _Ctx()

    def fake_open_browser(settings: Any, selectors: Any) -> FakePage:
        captured["selectors"] = selectors
        return FakePage()

    monkeypatch.setattr(ps, "load_selectors", fake_load_selectors)
    monkeypatch.setattr(ps, "open_browser", fake_open_browser)
    monkeypatch.setattr(ps, "navigate_to", lambda *_a, **_k: None)
    monkeypatch.setattr(ps, "fill_form", lambda *_a, **_k: None)
    monkeypatch.setattr(ps, "close_browser", lambda: None)

    validation = validate(
        {"operation": "2 + 3", "result": 5, "observation": "x"},
        PilotSmokeData,
    )
    llm = _make_llm("approve", 0.95)

    ps._submit_to_httpbin(_make_ctx(), validation, llm)

    assert "login" not in captured["selectors"]
    assert "pilot_smoke" in captured["selectors"]
