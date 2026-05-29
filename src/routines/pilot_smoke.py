"""Rotina-piloto E2E: Calculadora (desktop) → LLM (intel) → httpbin (web).

Exercita o chassis completo do robô (M0-M4) usando alvos neutros — não
automatiza processo Consigaz. Serve de template para a rotina TOTVS de M6.

Sequência (ver design.md §2):
    desktop → validate → call_llm → decide → [dry-run gate] → web submit
"""

from __future__ import annotations

from typing import Any

from desktop import (
    InteractionError,
    PlatformError,
    TemplateNotFoundError,
    click_at_template,
    extract_via_clipboard,
    get_platform_adapter,
    wait_for_template,
)
from intelligence import (
    Action,
    Decision,
    LLMResult,
    ValidationResult,
    call_llm,
    decide,
    validate,
)
from intelligence.schemas.pilot_smoke import PilotSmokeData, PilotSmokeLLM
from orchestrator.context import RoutineContext
from orchestrator.registry import register
from orchestrator.types import RoutineResult
from web import close_browser, fill_form, load_selectors, navigate_to, open_browser

_TEMPLATE_BASE = "assets/templates/pilot-smoke"
_HTTPBIN_FORM_URL = "https://httpbin.org/forms/post"
_OBSERVATION_FIXED = "cálculo de teste end-to-end"


@register("pilot-smoke")
def run(ctx: RoutineContext) -> RoutineResult:
    """Executa o pipeline E2E pilot-smoke.

    Caminhos:
        - validação inválida → ABORT_IN_DESKTOP
        - LLM reject/escalate / confidence baixa → action mapeada por `decide`
        - dry-run → early-return antes do Playwright
        - sucesso normal → PROCEED_TO_WEB com evidence completo
    """
    raw = _extract_from_calculator(ctx)

    validation = validate(raw, PilotSmokeData)
    if not validation.is_valid:
        decision = decide(validation, None)
        return RoutineResult(
            action=decision.action,
            evidence=_build_evidence(raw=raw, validation=validation),
        )

    llm = call_llm(
        prompt_name="pilot-smoke",
        params=raw,
        response_model=PilotSmokeLLM,
        settings=ctx.settings,
    )
    decision = decide(validation, llm, min_confidence=ctx.settings.llm_min_confidence)

    if decision.action is not Action.PROCEED_TO_WEB:
        return RoutineResult(
            action=decision.action,
            evidence=_build_evidence(
                raw=raw, validation=validation, llm=llm, decision=decision
            ),
        )

    if ctx.dry_run:
        ctx.logger.info("pilot_smoke_dry_run_skip_web")
        return RoutineResult(
            action=Action.PROCEED_TO_WEB,
            evidence=_build_evidence(
                raw=raw,
                validation=validation,
                llm=llm,
                decision=decision,
                dry_run=True,
            ),
        )

    web_info = _submit_to_httpbin(ctx, validation, llm)
    return RoutineResult(
        action=Action.PROCEED_TO_WEB,
        evidence=_build_evidence(
            raw=raw,
            validation=validation,
            llm=llm,
            decision=decision,
            web=web_info,
        ),
    )


def _extract_from_calculator(ctx: RoutineContext) -> dict[str, Any]:
    """Abre Calculadora, digita 2+3, extrai resultado via clipboard."""
    try:
        adapter = get_platform_adapter()
        adapter.launch_app("Calculator")
        adapter.focus_window("Calculator")
        wait_for_template(f"{_TEMPLATE_BASE}/window_titlebar.png")

        for element in ("btn_2", "btn_plus", "btn_3", "btn_equals"):
            click_at_template(f"{_TEMPLATE_BASE}/{element}.png")

        raw_result = extract_via_clipboard(adapter).strip()
    except (TemplateNotFoundError, InteractionError, PlatformError):
        raise

    try:
        parsed_result = int(raw_result)
    except ValueError:
        parsed_result = -1  # validação Pydantic deixa passar, mas LLM/router decidem

    return {
        "operation": "2 + 3",
        "result": parsed_result,
        "observation": _OBSERVATION_FIXED,
    }


def _submit_to_httpbin(
    ctx: RoutineContext,
    validation: ValidationResult,
    llm: LLMResult,
) -> dict[str, Any]:
    """Abre browser, preenche o form httpbin, submete e devolve URL/status finais."""
    data_model = validation.model
    assert isinstance(data_model, PilotSmokeData)
    llm_model = llm.model_instance
    assert isinstance(llm_model, PilotSmokeLLM)

    selectors = load_selectors()
    selectors_no_login = {k: v for k, v in selectors.items() if k != "login"}
    page = open_browser(ctx.settings, selectors=selectors_no_login)
    try:
        navigate_to(page, _HTTPBIN_FORM_URL)
        form_data: dict[str, str | None] = {
            "custname": "pilot-smoke",
            "custtel": "+55-00-0000-0000",
            "custemail": "pilot-smoke@example.invalid",
            "comments": f"{data_model.operation} = {data_model.result} | {llm_model.summary}",
        }
        fill_form(page, selectors, "pilot_smoke", form_data)

        from web.selectors import get_selector  # lazy

        submit_selector = get_selector(selectors, "pilot_smoke", "submit")
        with page.expect_navigation(wait_until="load", timeout=30_000):
            page.locator(submit_selector).first.click()

        final_url = page.url
        return {"final_url": final_url, "status": 200}
    finally:
        close_browser()


def _build_evidence(
    *,
    raw: dict[str, Any] | None = None,
    validation: ValidationResult | None = None,
    llm: LLMResult | None = None,
    decision: Decision | None = None,
    web: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Monta dict canônico de evidence (ver design.md §4).

    Apenas chaves safe — sem PII, sem prompt cru, sem resposta LLM crua.
    """
    evidence: dict[str, Any] = {"dry_run": dry_run}

    if raw is not None:
        evidence["operation"] = raw.get("operation")
        evidence["result"] = raw.get("result")

    if llm is not None and isinstance(llm.model_instance, PilotSmokeLLM):
        evidence["llm_decision"] = llm.model_instance.decision
        evidence["llm_confidence"] = llm.model_instance.confidence
        evidence["llm_summary"] = llm.model_instance.summary

    if web is not None:
        evidence["web_final_url"] = web.get("final_url")
        evidence["web_status"] = web.get("status")

    return evidence


__all__ = ["run"]
