"""Cliente OpenAI com retry, CostTracker e resposta tipada.

Premissa de thread-safety: o orquestrador v1 é single-thread. Cliente OpenAI e
CostTracker são globais de módulo. Se M4 introduzir threading, refatorar para
context manager.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, cast

import openai
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import Settings
from intelligence.exceptions import (
    LLMConfigError,
    LLMRequestError,
    LLMResponseSchemaError,
    LLMUnavailableError,
    TokenBudgetExceededError,
)
from intelligence.prompts import load as load_prompt
from intelligence.prompts import render as render_prompt
from intelligence.types import LLMResult
from logger.setup import get_logger

log = get_logger(__name__)

_client: openai.OpenAI | None = None
_cost_tracker: CostTracker | None = None


@dataclass
class CostTracker:
    """Rastreia tokens e USD acumulados de uma execução (rotina)."""

    token_hard_cap: int
    cost_warning_usd: float
    model_prices: dict[str, tuple[float, float]]
    tokens_used: int = 0
    cost_usd: float = 0.0
    warning_emitted: bool = field(default=False)

    def check_before(self, estimated_tokens: int) -> None:
        if self.tokens_used + estimated_tokens > self.token_hard_cap:
            raise TokenBudgetExceededError(
                tokens_used=self.tokens_used,
                tokens_pending=estimated_tokens,
                cap=self.token_hard_cap,
            )

    def add_after(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        self.tokens_used += prompt_tokens + completion_tokens
        price_in, price_out = self.model_prices.get(model, (0.0, 0.0))
        cost = (prompt_tokens * price_in + completion_tokens * price_out) / 1000
        self.cost_usd += cost
        if self.cost_usd > self.cost_warning_usd and not self.warning_emitted:
            log.warning(
                "llm_cost_warning",
                cost_usd_accumulated=self.cost_usd,
                cost_warning_threshold_usd=self.cost_warning_usd,
            )
            self.warning_emitted = True
        return cost


def _get_client(settings: Settings) -> openai.OpenAI:
    global _client
    if _client is None:
        api_key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key is not None
            else None
        )
        if not api_key:
            raise LLMConfigError("OPENAI_API_KEY ausente em keyring e .env")
        _client = openai.OpenAI(api_key=api_key)
    return _client


def reset_for_new_execution(settings: Settings) -> None:
    """Orquestrador chama no início de cada rotina; zera o cost tracker."""
    global _cost_tracker
    _cost_tracker = CostTracker(
        token_hard_cap=settings.llm_token_hard_cap,
        cost_warning_usd=settings.llm_cost_warning_usd,
        model_prices=dict(settings.llm_model_prices),
    )


def _reset_client_for_tests() -> None:
    """Limpa singletons. Uso exclusivo de fixtures de teste."""
    global _client, _cost_tracker
    _client = None
    _cost_tracker = None


def _get_tracker() -> CostTracker:
    if _cost_tracker is None:
        raise LLMConfigError(
            "reset_for_new_execution() não foi chamado antes de call_llm()"
        )
    return _cost_tracker


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, openai.RateLimitError):
        return True
    if isinstance(exc, openai.APIStatusError):
        return 500 <= exc.status_code < 600
    return False


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def _send_request(
    client: openai.OpenAI,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
) -> Any:
    return client.chat.completions.create(
        model=model,
        messages=cast(Any, messages),
        temperature=temperature,
        response_format={"type": "json_object"},
    )


def call_llm(
    prompt_name: str,
    params: dict[str, Any],
    response_model: type[BaseModel] | None,
    settings: Settings,
) -> LLMResult:
    """Carrega prompt, chama OpenAI com retry, parseia resposta no `response_model`.

    Sanitização: NUNCA loga o conteúdo do prompt nem da resposta crua.
    Apenas metadados (nome, versão, tokens, custo, latência).
    """
    prompt = load_prompt(prompt_name, settings.llm_prompts_dir)
    rendered = render_prompt(prompt, params)
    model = prompt.model or settings.llm_default_model
    temperature = (
        prompt.temperature
        if prompt.temperature is not None
        else settings.llm_default_temperature
    )
    tracker = _get_tracker()

    # Estimativa conservadora: ~4 chars/token + buffer para resposta
    estimated_tokens = max(1, len(rendered) // 4) + 500
    tracker.check_before(estimated_tokens)

    client = _get_client(settings)
    messages: list[dict[str, str]] = [{"role": "user", "content": rendered}]

    raw_content = ""
    latency_ms = 0
    usage: Any = None
    instance: BaseModel | str = ""

    for attempt in range(3):
        try:
            t0 = time.perf_counter()
            response = _send_request(client, model, messages, temperature)
        except openai.RateLimitError as e:
            raise LLMUnavailableError(last_exception=e) from e
        except openai.APIStatusError as e:
            if 500 <= e.status_code < 600:
                raise LLMUnavailableError(last_exception=e) from e
            raise LLMRequestError(
                status_code=e.status_code, message=str(e)
            ) from e
        except RetryError as e:
            raise LLMUnavailableError(last_exception=e) from e

        latency_ms = int((time.perf_counter() - t0) * 1000)
        raw_content = response.choices[0].message.content or ""
        usage = response.usage

        if response_model is None:
            instance = raw_content
            break
        try:
            instance = response_model.model_validate_json(raw_content)
            break
        except PydanticValidationError as e:
            if attempt == 2:
                raise LLMResponseSchemaError(
                    raw_response=raw_content,
                    validation_errors=[str(err) for err in e.errors()],
                ) from e
            continue

    cost = tracker.add_after(model, usage.prompt_tokens, usage.completion_tokens)

    log.info(
        "llm_call",
        prompt_name=prompt.name,
        prompt_version=prompt.version,
        model=model,
        tokens_in=usage.prompt_tokens,
        tokens_out=usage.completion_tokens,
        cost_usd_estimate=cost,
        latency_ms=latency_ms,
    )

    return LLMResult(
        model_instance=instance,
        usage_tokens_in=usage.prompt_tokens,
        usage_tokens_out=usage.completion_tokens,
        cost_usd_estimate=cost,
        latency_ms=latency_ms,
        prompt_name=prompt.name,
        prompt_version=prompt.version,
        model_used=model,
    )
