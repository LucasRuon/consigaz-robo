"""Testes da hierarquia IntelligenceError."""

from __future__ import annotations

from pathlib import Path

import pytest

from intelligence.exceptions import (
    IntelligenceError,
    LLMConfigError,
    LLMError,
    LLMRequestError,
    LLMResponseSchemaError,
    LLMUnavailableError,
    PromptError,
    PromptMetadataError,
    PromptNameError,
    PromptNotFoundError,
    PromptRenderError,
    RouterContractError,
    SchemaNotRegisteredError,
    TokenBudgetExceededError,
    ValidationCodeError,
)


def test_base_is_runtime_error() -> None:
    assert issubclass(IntelligenceError, RuntimeError)


@pytest.mark.parametrize(
    "cls",
    [
        ValidationCodeError,
        PromptError,
        PromptNotFoundError,
        PromptMetadataError,
        PromptRenderError,
        PromptNameError,
        LLMError,
        LLMConfigError,
        LLMUnavailableError,
        LLMRequestError,
        LLMResponseSchemaError,
        TokenBudgetExceededError,
        RouterContractError,
        SchemaNotRegisteredError,
    ],
)
def test_all_subclass_of_intelligence_error(cls: type) -> None:
    assert issubclass(cls, IntelligenceError)


def test_prompt_subclasses_inherit_prompt_error() -> None:
    for cls in (
        PromptNotFoundError,
        PromptMetadataError,
        PromptRenderError,
        PromptNameError,
    ):
        assert issubclass(cls, PromptError)


def test_llm_subclasses_inherit_llm_error() -> None:
    for cls in (
        LLMConfigError,
        LLMUnavailableError,
        LLMRequestError,
        LLMResponseSchemaError,
        TokenBudgetExceededError,
    ):
        assert issubclass(cls, LLMError)


def test_validation_code_error_attrs() -> None:
    inner = TypeError("boom")
    err = ValidationCodeError(schema="MeuSchema", original_exception=inner)
    assert err.schema == "MeuSchema"
    assert err.original_exception is inner
    assert "MeuSchema" in str(err)


def test_prompt_not_found_error_attrs() -> None:
    p = Path("/tmp/foo.md")
    err = PromptNotFoundError(name="foo", path=p)
    assert err.name == "foo"
    assert err.path == p


def test_prompt_metadata_error_attrs() -> None:
    err = PromptMetadataError(name="foo", reason="version ausente")
    assert err.name == "foo"
    assert err.reason == "version ausente"


def test_prompt_render_error_attrs() -> None:
    err = PromptRenderError(name="foo", missing=["a", "b"])
    assert err.missing == ["a", "b"]


def test_prompt_name_error_attrs() -> None:
    err = PromptNameError(name="../bad")
    assert err.name == "../bad"


def test_llm_unavailable_attrs() -> None:
    inner = ConnectionError("net")
    err = LLMUnavailableError(last_exception=inner)
    assert err.last_exception is inner


def test_llm_request_error_attrs() -> None:
    err = LLMRequestError(status_code=400, message="bad request")
    assert err.status_code == 400
    assert err.message == "bad request"


def test_token_budget_attrs() -> None:
    err = TokenBudgetExceededError(tokens_used=50, tokens_pending=60, cap=100)
    assert err.tokens_used == 50
    assert err.tokens_pending == 60
    assert err.cap == 100
    assert "100" in str(err)


def test_router_contract_attrs() -> None:
    err = RouterContractError(expected_field="decision", got_type="dict")
    assert err.expected_field == "decision"
    assert err.got_type == "dict"


def test_schema_not_registered_attrs() -> None:
    err = SchemaNotRegisteredError(name="x", known=["a", "b"])
    assert err.name == "x"
    assert err.known == ["a", "b"]


def test_response_schema_truncates_short_raw() -> None:
    raw = '{"x": 1}'
    err = LLMResponseSchemaError(raw_response=raw, validation_errors=["e1"])
    assert err.raw_response == raw + "[SANITIZED]"
    assert "[SANITIZED]" in str(err)


def test_response_schema_truncates_long_raw() -> None:
    raw = "A" * 500
    err = LLMResponseSchemaError(raw_response=raw, validation_errors=[])
    # 200 chars + ...[SANITIZED]
    assert err.raw_response.startswith("A" * 200)
    assert err.raw_response.endswith("...[SANITIZED]")
    assert len(err.raw_response) == 200 + len("...[SANITIZED]")
    # Nada original do tail (>200 chars) vaza
    assert "A" * 250 not in str(err)


def test_instantiation_does_not_crash() -> None:
    LLMConfigError("missing key")
    PromptError("generic")
