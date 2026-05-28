"""Testes de intelligence.llm: cliente OpenAI mockado, retry, CostTracker."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import openai
import pytest
import structlog
from pydantic import BaseModel, SecretStr
from tenacity import wait_none

from config.settings import Settings
from intelligence import llm as llm_module
from intelligence.exceptions import (
    LLMConfigError,
    LLMRequestError,
    LLMResponseSchemaError,
    LLMUnavailableError,
    TokenBudgetExceededError,
)
from intelligence.llm import CostTracker, call_llm, reset_for_new_execution


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_llm_state() -> Iterator[None]:
    llm_module._reset_client_for_tests()
    yield
    llm_module._reset_client_for_tests()


@pytest.fixture(autouse=True)
def _disable_tenacity_sleep() -> Iterator[None]:
    """Zera o wait do retry para que os testes rodem rápido."""
    original = llm_module._send_request.retry.wait
    llm_module._send_request.retry.wait = wait_none()
    yield
    llm_module._send_request.retry.wait = original


@pytest.fixture(autouse=True)
def _structlog_to_stdlib() -> Iterator[None]:
    """Garante que logs do structlog cheguem ao caplog (stdlib)."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.KeyValueRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    yield
    structlog.reset_defaults()


@pytest.fixture
def prompt_dir(tmp_path: Path) -> Path:
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "p.md").write_text(
        "---\nversion: 1.0.0\nmodel: gpt-4o-mini\ntemperature: 0.0\n---\n"
        "echo {input}",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def settings(prompt_dir: Path) -> Settings:
    return Settings(
        openai_api_key=SecretStr("sk-test"),
        llm_prompts_dir=prompt_dir,
        llm_token_hard_cap=100_000,
        llm_cost_warning_usd=1.00,
        llm_model_prices={"gpt-4o-mini": (0.001, 0.002)},
    )


def _ok_response(content: str = '{"decision": "approve", "confidence": 0.9}') -> MagicMock:
    r = MagicMock()
    r.choices = [MagicMock()]
    r.choices[0].message.content = content
    r.usage.prompt_tokens = 100
    r.usage.completion_tokens = 20
    r.usage.total_tokens = 120
    return r


def _api_status_error(code: int) -> openai.APIStatusError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(code, request=request)
    return openai.APIStatusError(f"{code}", response=response, body=None)


def _rate_limit_error() -> openai.RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return openai.RateLimitError("429", response=response, body=None)


def _patch_send(monkeypatch: pytest.MonkeyPatch, side_effect: Any) -> MagicMock:
    mock = MagicMock(side_effect=side_effect if callable(side_effect) else side_effect)
    monkeypatch.setattr(llm_module._send_request, "__wrapped__", mock)
    # tenacity wraps the function; precisamos substituir o callable de fato
    monkeypatch.setattr(llm_module, "_send_request", _wrap_with_retry(mock))
    return mock


def _wrap_with_retry(fn: MagicMock):
    """Re-aplica o decorator de retry para que o mock respeite a política."""
    from tenacity import retry, retry_if_exception, stop_after_attempt, wait_none

    return retry(
        wait=wait_none(),
        stop=stop_after_attempt(4),
        retry=retry_if_exception(llm_module._is_retryable),
        reraise=True,
    )(fn)


def _patch_client(monkeypatch: pytest.MonkeyPatch, mock_create: MagicMock) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create = mock_create
    monkeypatch.setattr(llm_module, "_client", client)
    return client


# Importes adicionais (Any usado em _patch_send)
from typing import Any  # noqa: E402


# ── Tests: client ────────────────────────────────────────────────────────


def test_get_client_raises_without_api_key() -> None:
    s = Settings()  # openai_api_key=None
    with pytest.raises(LLMConfigError):
        llm_module._get_client(s)


def test_get_client_caches(settings: Settings) -> None:
    c1 = llm_module._get_client(settings)
    c2 = llm_module._get_client(settings)
    assert c1 is c2


# ── Tests: reset / tracker ───────────────────────────────────────────────


def test_call_llm_without_reset_raises(settings: Settings) -> None:
    with pytest.raises(LLMConfigError):
        call_llm("p", {"input": "x"}, None, settings)


def test_reset_zeroes_tracker(settings: Settings) -> None:
    reset_for_new_execution(settings)
    t = llm_module._get_tracker()
    assert t.tokens_used == 0
    assert t.cost_usd == 0.0
    assert t.warning_emitted is False


def test_cost_tracker_check_before_raises() -> None:
    t = CostTracker(token_hard_cap=100, cost_warning_usd=1.0, model_prices={})
    t.tokens_used = 50
    with pytest.raises(TokenBudgetExceededError) as exc:
        t.check_before(60)
    assert exc.value.tokens_used == 50
    assert exc.value.tokens_pending == 60
    assert exc.value.cap == 100


def test_cost_tracker_add_after_accumulates() -> None:
    t = CostTracker(
        token_hard_cap=10_000,
        cost_warning_usd=1.0,
        model_prices={"m": (0.001, 0.002)},
    )
    cost = t.add_after("m", 1000, 500)
    assert t.tokens_used == 1500
    # (1000*0.001 + 500*0.002)/1000 = (1.0 + 1.0)/1000 = 0.002
    assert cost == pytest.approx(0.002)
    assert t.cost_usd == pytest.approx(0.002)


def test_cost_tracker_unknown_model_zero_price() -> None:
    t = CostTracker(token_hard_cap=10_000, cost_warning_usd=1.0, model_prices={})
    cost = t.add_after("desconhecido", 100, 100)
    assert cost == 0.0


# ── Tests: call_llm happy path ───────────────────────────────────────────


def test_call_llm_happy_path_with_response_model(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    class R(BaseModel):
        decision: str
        confidence: float

    reset_for_new_execution(settings)
    create = MagicMock(return_value=_ok_response())
    _patch_client(monkeypatch, create)

    result = call_llm("p", {"input": "x"}, R, settings)
    assert isinstance(result.model_instance, R)
    assert result.model_instance.decision == "approve"
    assert result.usage_tokens_in == 100
    assert result.usage_tokens_out == 20
    assert result.model_used == "gpt-4o-mini"
    assert result.prompt_name == "p"
    assert result.prompt_version == "1.0.0"
    create.assert_called_once()


def test_call_llm_with_no_response_model_returns_raw_string(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    reset_for_new_execution(settings)
    create = MagicMock(return_value=_ok_response("texto livre"))
    _patch_client(monkeypatch, create)

    result = call_llm("p", {"input": "x"}, None, settings)
    assert result.model_instance == "texto livre"


# ── Tests: retry behavior ────────────────────────────────────────────────


def test_retry_on_429_then_success(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    reset_for_new_execution(settings)
    ok = _ok_response()
    create = MagicMock(side_effect=[_rate_limit_error(), _rate_limit_error(), ok])
    _patch_client(monkeypatch, create)

    result = call_llm("p", {"input": "x"}, None, settings)
    assert result.model_instance == ok.choices[0].message.content
    assert create.call_count == 3


def test_retry_on_5xx_then_success(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    reset_for_new_execution(settings)
    create = MagicMock(
        side_effect=[_api_status_error(500), _api_status_error(502), _ok_response()]
    )
    _patch_client(monkeypatch, create)
    result = call_llm("p", {"input": "x"}, None, settings)
    assert result.usage_tokens_in == 100
    assert create.call_count == 3


def test_5xx_exhausted_raises_llm_unavailable(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    reset_for_new_execution(settings)
    create = MagicMock(side_effect=_api_status_error(500))
    _patch_client(monkeypatch, create)
    with pytest.raises(LLMUnavailableError):
        call_llm("p", {"input": "x"}, None, settings)
    assert create.call_count == 4  # stop_after_attempt(4)


def test_400_raises_llm_request_error_no_retry(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    reset_for_new_execution(settings)
    create = MagicMock(side_effect=_api_status_error(400))
    _patch_client(monkeypatch, create)
    with pytest.raises(LLMRequestError) as exc:
        call_llm("p", {"input": "x"}, None, settings)
    assert exc.value.status_code == 400
    assert create.call_count == 1


# ── Tests: response schema retry ─────────────────────────────────────────


def test_schema_mismatch_retries_then_succeeds(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    class R(BaseModel):
        decision: str
        confidence: float

    reset_for_new_execution(settings)
    bad = _ok_response('{"wrong": "shape"}')
    ok = _ok_response('{"decision": "approve", "confidence": 0.9}')
    create = MagicMock(side_effect=[bad, ok])
    _patch_client(monkeypatch, create)
    result = call_llm("p", {"input": "x"}, R, settings)
    assert isinstance(result.model_instance, R)
    assert create.call_count == 2


def test_schema_mismatch_persists_raises(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    class R(BaseModel):
        decision: str

    reset_for_new_execution(settings)
    create = MagicMock(return_value=_ok_response('{"x": 1}'))
    _patch_client(monkeypatch, create)
    with pytest.raises(LLMResponseSchemaError):
        call_llm("p", {"input": "x"}, R, settings)
    assert create.call_count == 3  # 1 + 2 retries


# ── Tests: budget guard ──────────────────────────────────────────────────


def test_token_hard_cap_blocks_before_call(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    # Cap minúsculo: prompt "echo x" (~7 chars / 4 = 1) + buffer 500 > 100
    reset_for_new_execution(
        Settings(
            openai_api_key=SecretStr("sk-test"),
            llm_prompts_dir=settings.llm_prompts_dir,
            llm_token_hard_cap=100,
            llm_cost_warning_usd=1.0,
            llm_model_prices={"gpt-4o-mini": (0.001, 0.002)},
        )
    )
    create = MagicMock(return_value=_ok_response())
    _patch_client(monkeypatch, create)
    with pytest.raises(TokenBudgetExceededError):
        call_llm("p", {"input": "x"}, None, settings)
    create.assert_not_called()


def test_cost_warning_emitted_once(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Threshold baixíssimo + preço alto → warning na 1ª chamada
    s = Settings(
        openai_api_key=SecretStr("sk-test"),
        llm_prompts_dir=settings.llm_prompts_dir,
        llm_token_hard_cap=100_000,
        llm_cost_warning_usd=0.0001,
        llm_model_prices={"gpt-4o-mini": (0.01, 0.01)},
    )
    reset_for_new_execution(s)
    create = MagicMock(return_value=_ok_response())
    _patch_client(monkeypatch, create)

    with caplog.at_level(logging.WARNING):
        call_llm("p", {"input": "x"}, None, s)
        call_llm("p", {"input": "x"}, None, s)

    warnings = [r for r in caplog.records if "llm_cost_warning" in r.getMessage()]
    assert len(warnings) == 1


# ── Tests: sanitização ─────────────────────────────────────────────────


def test_log_does_not_leak_prompt_content(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reset_for_new_execution(settings)
    create = MagicMock(return_value=_ok_response())
    _patch_client(monkeypatch, create)

    sensitive = "DADOS_SENSIVEIS_XYZ"
    with caplog.at_level(logging.DEBUG):
        call_llm("p", {"input": sensitive}, None, settings)

    for record in caplog.records:
        msg = record.getMessage()
        assert sensitive not in msg, f"vazou em {record.levelname}: {msg!r}"
        assert sensitive not in str(record.__dict__)


def test_log_includes_metadata_keys(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    reset_for_new_execution(settings)
    create = MagicMock(return_value=_ok_response())
    _patch_client(monkeypatch, create)
    with caplog.at_level(logging.INFO):
        call_llm("p", {"input": "x"}, None, settings)
    info_records = [r.getMessage() for r in caplog.records if "llm_call" in r.getMessage()]
    assert info_records
    combined = " ".join(info_records)
    for key in ("prompt_name", "prompt_version", "model", "tokens_in", "tokens_out"):
        assert key in combined
