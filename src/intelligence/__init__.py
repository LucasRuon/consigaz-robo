"""intelligence — camada determinística + LLM entre desktop/ e web/.

API pública:
    validate(data, schema) -> ValidationResult
    call_llm(prompt_name, params, response_model, settings) -> LLMResult
    decide(validation, llm_result, *, min_confidence) -> Decision
    reset_for_new_execution(settings) -> None
    load_prompt(name, prompts_dir=None) -> Prompt
    render_prompt(prompt, params) -> str
    register_schema(name) / get_schema(name) / list_schemas()

Tipos:
    Action, ValidationResult, LLMResult, Decision, Prompt

Exceções:
    IntelligenceError (base), ValidationCodeError,
    PromptError + subclasses, LLMError + subclasses,
    RouterContractError, SchemaNotRegisteredError
"""

from __future__ import annotations

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
from intelligence.llm import call_llm, reset_for_new_execution
from intelligence.prompts import Prompt
from intelligence.prompts import load as load_prompt
from intelligence.prompts import render as render_prompt
from intelligence.router import decide
from intelligence.schemas import get_schema, list_schemas
from intelligence.schemas import register as register_schema
from intelligence.types import Action, Decision, LLMResult, ValidationResult
from intelligence.validation import validate

__all__ = [
    "Action",
    "Decision",
    "IntelligenceError",
    "LLMConfigError",
    "LLMError",
    "LLMRequestError",
    "LLMResponseSchemaError",
    "LLMResult",
    "LLMUnavailableError",
    "Prompt",
    "PromptError",
    "PromptMetadataError",
    "PromptNameError",
    "PromptNotFoundError",
    "PromptRenderError",
    "RouterContractError",
    "SchemaNotRegisteredError",
    "TokenBudgetExceededError",
    "ValidationCodeError",
    "ValidationResult",
    "call_llm",
    "decide",
    "get_schema",
    "list_schemas",
    "load_prompt",
    "register_schema",
    "render_prompt",
    "reset_for_new_execution",
    "validate",
]
