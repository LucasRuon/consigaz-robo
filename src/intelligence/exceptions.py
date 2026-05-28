"""Hierarquia de exceções do módulo `intelligence`."""

from __future__ import annotations

from pathlib import Path

_SANITIZED_TRUNCATE = 200


class IntelligenceError(RuntimeError):
    """Base — qualquer falha do módulo intelligence."""


class ValidationCodeError(IntelligenceError):
    """Bug em validador customizado (não erro de dado)."""

    def __init__(self, schema: str, original_exception: BaseException) -> None:
        super().__init__(
            f"Erro de código no validador {schema!r}: "
            f"{type(original_exception).__name__}: {original_exception}"
        )
        self.schema = schema
        self.original_exception = original_exception


# ── Prompts ──────────────────────────────────────────────────────────────


class PromptError(IntelligenceError):
    """Base para erros de carregamento/render de prompts."""


class PromptNotFoundError(PromptError):
    """Arquivo .md de prompt não encontrado."""

    def __init__(self, name: str, path: Path) -> None:
        super().__init__(f"Prompt {name!r} não encontrado em {path}")
        self.name = name
        self.path = path


class PromptMetadataError(PromptError):
    """Frontmatter ausente, malformado ou faltando campos obrigatórios."""

    def __init__(self, name: str, reason: str) -> None:
        super().__init__(f"Frontmatter inválido em prompt {name!r}: {reason}")
        self.name = name
        self.reason = reason


class PromptRenderError(PromptError):
    """Placeholders ausentes em `params` durante `render()`."""

    def __init__(self, name: str, missing: list[str]) -> None:
        super().__init__(
            f"Placeholders ausentes ao renderizar prompt {name!r}: {missing}"
        )
        self.name = name
        self.missing = missing


class PromptNameError(PromptError):
    """Nome de prompt com path traversal ou inválido."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Nome de prompt inválido: {name!r}")
        self.name = name


# ── LLM ──────────────────────────────────────────────────────────────────


class LLMError(IntelligenceError):
    """Base para erros de chamadas ao LLM."""


class LLMConfigError(LLMError):
    """Configuração ausente ou inválida (ex: API key)."""


class LLMUnavailableError(LLMError):
    """Esgotou tentativas em erros retentáveis (429/5xx)."""

    def __init__(self, last_exception: BaseException) -> None:
        super().__init__(
            f"LLM indisponível após retries: "
            f"{type(last_exception).__name__}: {last_exception}"
        )
        self.last_exception = last_exception


class LLMRequestError(LLMError):
    """4xx (≠429) — erro de request sem retry."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"LLM request HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class LLMResponseSchemaError(LLMError):
    """Resposta não bate com `response_model` após retries."""

    def __init__(self, raw_response: str, validation_errors: list[str]) -> None:
        sanitized = raw_response[:_SANITIZED_TRUNCATE]
        if len(raw_response) > _SANITIZED_TRUNCATE:
            sanitized += "...[SANITIZED]"
        else:
            sanitized += "[SANITIZED]"
        super().__init__(
            f"Resposta do LLM não bate com schema: errors={validation_errors}; "
            f"raw={sanitized}"
        )
        self.raw_response = sanitized
        self.validation_errors = validation_errors


class TokenBudgetExceededError(LLMError):
    """Hard cap em tokens seria estourado pela próxima chamada."""

    def __init__(self, tokens_used: int, tokens_pending: int, cap: int) -> None:
        super().__init__(
            f"Cap de tokens estourado: usados={tokens_used}, "
            f"pendentes={tokens_pending}, cap={cap}"
        )
        self.tokens_used = tokens_used
        self.tokens_pending = tokens_pending
        self.cap = cap


# ── Router / Schemas ─────────────────────────────────────────────────────


class RouterContractError(IntelligenceError):
    """LLM result não satisfaz o contrato esperado pelo router."""

    def __init__(self, expected_field: str, got_type: str) -> None:
        super().__init__(
            f"Router esperava campo {expected_field!r}, "
            f"recebeu instância de {got_type}"
        )
        self.expected_field = expected_field
        self.got_type = got_type


class SchemaNotRegisteredError(IntelligenceError):
    """Nome de schema referenciado por prompt não está no registry."""

    def __init__(self, name: str, known: list[str]) -> None:
        super().__init__(
            f"Schema {name!r} não registrado. Conhecidos: {known}"
        )
        self.name = name
        self.known = known
