# M3 — Camada de Inteligência: Design

**Spec**: `.specs/features/m3-intelligence-layer/spec.md`

---

## Visão Geral

O módulo `intelligence/` é a ponte determinística + LLM entre `desktop/` e `web/`. Segue o mesmo padrão funcional do resto do projeto (sem classes-singleton, sem estado global salvo o cliente OpenAI e o cost tracker da execução corrente).

Sequência canônica chamada pelo orquestrador (M4):

```
desktop.extract()  →  dict
        │
        ▼
intelligence.validate(data, schema)        →  ValidationResult
        │ (is_valid)
        ▼
intelligence.call_llm(prompt, params, ResponseModel)  →  LLMResult | None
        │
        ▼
intelligence.decide(validation, llm_result)  →  Decision
        │
        ▼
   Action.PROCEED_TO_WEB  →  web.fill_form(...)
   Action.ABORT_IN_DESKTOP  →  encerra rotina (log estruturado)
   Action.RAISE_EXCEPTION  →  re-lança para o orquestrador tratar
```

```
src/intelligence/
├── __init__.py            # exports públicos
├── exceptions.py          # hierarquia IntelligenceError
├── validation.py          # validate(data, schema) → ValidationResult
├── analysis.py            # helpers Pandas (validate_range, compare_against_history)
├── prompts.py             # load(name) → Prompt; render(params)
├── llm.py                 # call_llm(...) + CostTracker
├── router.py              # decide(validation, llm_result) → Decision
├── types.py               # ValidationResult, LLMResult, Decision, Action
└── schemas/
    ├── __init__.py        # registry: nome → classe Pydantic
    └── (futuro: schemas de rotinas vivem aqui)

config/prompts/
└── (futuro: <nome>.md com frontmatter — vazio no M3, alimentado em M5)

tests/intelligence/
├── __init__.py
├── test_exceptions.py
├── test_validation.py
├── test_analysis.py
├── test_prompts.py
├── test_llm.py
├── test_router.py
└── fixtures/
    └── prompts/           # .md de exemplo usados nos testes
```

---

## Decisões Arquiteturais

### Pydantic v2 puro para schemas; Pandas como helper opcional

Schemas de validação são subclasses de `pydantic.BaseModel` com `model_config = {"extra": "forbid", "strict": True}`. Análises agregadas (comparar valor contra histórico, validar range numérico) ficam em `analysis.py` como **funções puras**, separadas do caminho crítico. Quem precisa importa; quem não precisa nem carrega Pandas.

**Por que separar**: importar Pandas é caro (~200ms no cold start). Validação por schema acontece em toda rotina; análises agregadas só em algumas. Manter `validation.py` sem dependência de Pandas dá cold start mais rápido para rotinas simples.

### Cliente OpenAI: instância única lazy + CostTracker por execução

```python
# llm.py
_client: openai.OpenAI | None = None
_cost_tracker: CostTracker | None = None

def _get_client(settings: Settings) -> openai.OpenAI:
    global _client
    if _client is None:
        api_key = secrets.get("OPENAI_API_KEY") or settings.openai_api_key
        if not api_key:
            raise LLMConfigError("OPENAI_API_KEY ausente em keyring e .env")
        _client = openai.OpenAI(api_key=api_key)
    return _client

def reset_for_new_execution(settings: Settings) -> None:
    """Chamado pelo orquestrador no início de cada rotina — zera o cost tracker."""
    global _cost_tracker
    _cost_tracker = CostTracker(
        token_hard_cap=settings.llm_token_hard_cap,
        cost_warning_usd=settings.llm_cost_warning_usd,
        model_prices=settings.llm_model_prices,
    )
```

O orquestrador é single-thread (decisão STATE 2026-05-28: single-host). Estado global do cliente + tracker é seguro nessa premissa. Documentado em `llm.py` no topo.

### Retry exponencial com Tenacity (somente em 429/5xx + schema-mismatch)

```python
from tenacity import (
    retry, wait_exponential, stop_after_attempt,
    retry_if_exception_type, retry_if_exception
)
import openai

def _is_retryable_status(exc: BaseException) -> bool:
    if isinstance(exc, openai.RateLimitError):
        return True
    if isinstance(exc, openai.APIStatusError):
        return 500 <= exc.status_code < 600
    return False

@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    retry=retry_if_exception(_is_retryable_status),
    reraise=True,
)
def _send_request(client, model, messages, temperature):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
```

Schema-mismatch (resposta JSON válido mas faltando campos do `response_model`) tem retry separado, máximo 2x, **não-exponencial** (retentar imediatamente força a LLM a regenerar):

```python
for attempt in range(3):  # 1 original + 2 retries
    raw = _send_request(...)
    try:
        return response_model.model_validate_json(raw.choices[0].message.content)
    except pydantic.ValidationError as e:
        if attempt == 2:
            raise LLMResponseSchemaError(...) from e
        continue
```

### Prompts: parser inline (sem dependência de python-frontmatter)

Parser simples baseado em `re.match` para o delimitador `---` + `yaml.safe_load` (PyYAML já está no projeto via `pydantic-settings`? — verificar e adicionar como dep direta se necessário).

```python
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

def load(name: str, prompts_dir: Path | None = None) -> Prompt:
    if "/" in name or "\\" in name or ".." in name:
        raise PromptNameError(name=name)
    path = (prompts_dir or _default_prompts_dir()) / f"{name}.md"
    if not path.exists():
        raise PromptNotFoundError(name=name, path=path)
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise PromptMetadataError(name=name, reason="frontmatter ausente ou malformado")
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        raise PromptMetadataError(name=name, reason=str(e)) from e
    if "version" not in meta:
        raise PromptMetadataError(name=name, reason="campo 'version' obrigatório")
    return Prompt(
        name=name,
        template=match.group(2),
        version=str(meta["version"]),
        model=meta.get("model"),
        temperature=meta.get("temperature"),
        response_schema=meta.get("response_schema"),
    )
```

Render usa `str.format_map` com `_SafeDict` para detectar placeholders ausentes sem KeyError ruidoso:

```python
class _Placeholders(dict):
    def __init__(self):
        self.missing: list[str] = []
    def __missing__(self, key):
        self.missing.append(key)
        return "{" + key + "}"  # mantém literal para inspeção

def render(prompt: Prompt, params: dict[str, Any]) -> str:
    holder = _Placeholders()
    holder.update(params)
    rendered = prompt.template.format_map(holder)
    if holder.missing:
        raise PromptRenderError(name=prompt.name, missing=holder.missing)
    return rendered
```

### Router: função pura, table-driven

```python
def decide(
    validation: ValidationResult,
    llm_result: LLMResult | None = None,
    *,
    min_confidence: float = 0.7,
) -> Decision:
    if not validation.is_valid:
        return Decision(
            action=Action.ABORT_IN_DESKTOP,
            reason="dados inválidos",
            evidence={"errors": validation.errors},
            confidence=1.0,
        )
    if llm_result is None:
        return Decision(
            action=Action.PROCEED_TO_WEB,
            reason="validação ok, sem análise LLM necessária",
            evidence={"model": validation.model.model_dump(mode="json") if validation.model else {}},
            confidence=1.0,
        )
    instance = llm_result.model_instance
    if not hasattr(instance, "decision"):
        raise RouterContractError(
            expected_field="decision",
            got_type=type(instance).__name__,
        )
    confidence = float(getattr(instance, "confidence", 1.0))
    if confidence < min_confidence:
        return Decision(
            action=Action.RAISE_EXCEPTION,
            reason=f"confiança {confidence:.2f} abaixo do mínimo {min_confidence:.2f}",
            evidence={"llm": instance.model_dump(mode="json")},
            confidence=confidence,
        )
    return Decision(
        action=_ACTION_MAP[instance.decision],
        reason=getattr(instance, "reason", "decisão da LLM"),
        evidence={"llm": instance.model_dump(mode="json")},
        confidence=confidence,
    )

_ACTION_MAP = {
    "approve": Action.PROCEED_TO_WEB,
    "reject": Action.ABORT_IN_DESKTOP,
    "escalate": Action.RAISE_EXCEPTION,
}
```

Função recebe `min_confidence` como parâmetro opcional (não lê settings dentro) — preserva pureza para testes determinísticos. O orquestrador passa `settings.llm_min_confidence`.

### Sanitização de log estruturado

`call_llm` NUNCA loga `prompt_text` rendered nem `response.content`. Apenas metadados:

```python
log.info(
    "llm_call",
    extra={
        "prompt_name": prompt.name,
        "prompt_version": prompt.version,
        "model": model,
        "tokens_in": usage.prompt_tokens,
        "tokens_out": usage.completion_tokens,
        "cost_usd_estimate": cost,
        "latency_ms": latency_ms,
        # PROIBIDO: "prompt_text", "response_text", "params"
    },
)
```

Teste de sanitização verifica que nenhum log handler recebe `prompt_text` ou `response_text` em qualquer caminho de código.

---

## Interfaces Públicas

### `intelligence/validation.py`

```python
def validate(
    data: dict[str, Any] | None,
    schema: type[BaseModel],
) -> ValidationResult:
    """
    Valida `data` contra `schema` (Pydantic v2). Não lança em erro de dado —
    retorna `ValidationResult(is_valid=False, errors=[...])`.
    Lança `ValidationCodeError` se schema lança exceção não-`ValidationError`
    (separa bug de validador de dado inválido).
    """
```

### `intelligence/analysis.py`

```python
def validate_range(
    value: float | Decimal,
    lo: float | Decimal,
    hi: float | Decimal,
    field_name: str = "valor",
) -> str | None:
    """Retorna string de erro se fora do range; None se ok."""

def compare_against_history(
    value: float,
    series: pd.Series,
    threshold_std: float = 2.0,
) -> bool:
    """True se `value` está dentro de `threshold_std` desvios da média de `series`."""
```

### `intelligence/prompts.py`

```python
@dataclass(frozen=True)
class Prompt:
    name: str
    template: str
    version: str
    model: str | None
    temperature: float | None
    response_schema: str | None

def load(name: str, prompts_dir: Path | None = None) -> Prompt: ...
def render(prompt: Prompt, params: dict[str, Any]) -> str: ...
```

### `intelligence/llm.py`

```python
def call_llm(
    prompt_name: str,
    params: dict[str, Any],
    response_model: type[BaseModel] | None,
    settings: Settings,
) -> LLMResult: ...

def reset_for_new_execution(settings: Settings) -> None:
    """Orquestrador chama no início de cada rotina; zera o cost tracker."""

@dataclass
class CostTracker:
    token_hard_cap: int
    cost_warning_usd: float
    model_prices: dict[str, tuple[float, float]]
    tokens_used: int = 0
    cost_usd: float = 0.0
    warning_emitted: bool = False

    def check_before(self, estimated_tokens: int) -> None:
        if self.tokens_used + estimated_tokens > self.token_hard_cap:
            raise TokenBudgetExceededError(...)

    def add_after(self, model: str, usage: Usage) -> None:
        self.tokens_used += usage.total_tokens
        price_in, price_out = self.model_prices[model]
        self.cost_usd += (usage.prompt_tokens * price_in
                         + usage.completion_tokens * price_out) / 1000
        if self.cost_usd > self.cost_warning_usd and not self.warning_emitted:
            log.warning("llm_cost_warning", extra={...})
            self.warning_emitted = True
```

### `intelligence/router.py`

```python
def decide(
    validation: ValidationResult,
    llm_result: LLMResult | None = None,
    *,
    min_confidence: float = 0.7,
) -> Decision: ...
```

### `intelligence/types.py`

```python
class Action(str, Enum):
    PROCEED_TO_WEB = "proceed_to_web"
    ABORT_IN_DESKTOP = "abort_in_desktop"
    RAISE_EXCEPTION = "raise_exception"

class ValidationResult(BaseModel):
    is_valid: bool
    model: BaseModel | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    model_config = {"arbitrary_types_allowed": True}

class LLMResult(BaseModel):
    model_instance: BaseModel | str  # BaseModel se tipado, str se texto livre
    usage_tokens_in: int
    usage_tokens_out: int
    cost_usd_estimate: float
    latency_ms: int
    prompt_name: str
    prompt_version: str
    model_used: str
    model_config = {"arbitrary_types_allowed": True}

class Decision(BaseModel):
    action: Action
    reason: str
    evidence: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
```

### `intelligence/schemas/__init__.py` (registry)

```python
_REGISTRY: dict[str, type[BaseModel]] = {}

def register(name: str):
    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        _REGISTRY[name] = cls
        return cls
    return decorator

def get_schema(name: str) -> type[BaseModel]:
    if name not in _REGISTRY:
        raise SchemaNotRegisteredError(name=name, known=list(_REGISTRY))
    return _REGISTRY[name]
```

`prompts.load()` valida que `response_schema` (se declarado) está no registry chamando `get_schema(name)` — falha cedo se prompt referencia schema não registrado. Schemas de rotinas (M5) usam `@register("nome_referenciado_no_prompt")`.

---

## Hierarquia de Exceções

```
IntelligenceError(RuntimeError)              # base do módulo
├── ValidationCodeError                       # bug no validador (não erro de dado)
│       .schema: str
│       .original_exception: BaseException
├── PromptError
│       ├── PromptNotFoundError               # arquivo .md ausente
│       │       .name: str
│       │       .path: Path
│       ├── PromptMetadataError               # frontmatter inválido / version ausente
│       │       .name: str
│       │       .reason: str
│       ├── PromptRenderError                 # placeholders ausentes
│       │       .name: str
│       │       .missing: list[str]
│       └── PromptNameError                   # nome com traversal (/, .., \)
│               .name: str
├── LLMError
│       ├── LLMConfigError                    # API key ausente
│       ├── LLMUnavailableError               # esgotou retries
│       │       .last_exception: BaseException
│       ├── LLMRequestError                   # 4xx (≠429), sem retry
│       │       .status_code: int
│       ├── LLMResponseSchemaError            # resposta não bate response_model
│       │       .raw_response: str  # SANITIZADO antes de logar
│       │       .validation_errors: list[str]
│       └── TokenBudgetExceededError          # cap em tokens estouraria
│               .tokens_used: int
│               .tokens_pending: int
│               .cap: int
├── RouterContractError                       # LLM result não expõe .decision
│       .expected_field: str
│       .got_type: str
└── SchemaNotRegisteredError                  # response_schema do prompt não está no registry
        .name: str
        .known: list[str]
```

Note que `ValidationResult.is_valid=False` **não lança** — é um valor de retorno. Exceção só para bug de código (`ValidationCodeError`).

---

## Configurações Novas em `settings.py`

```python
class Settings(BaseSettings):
    # ... campos existentes (M0, M1, M2) ...

    # M3 — LLM
    openai_api_key: SecretStr | None = None     # fallback se keyring vazio
    llm_default_model: str = "gpt-4o-mini"
    llm_default_temperature: float = 0.0
    llm_min_confidence: float = 0.7
    llm_token_hard_cap: int = 100_000           # por execução
    llm_cost_warning_usd: float = 1.00          # por execução
    llm_prompts_dir: Path = Path("config/prompts")

    # Tabela de preços (USD por 1k tokens: input, output)
    # Atualizada manualmente quando OpenAI muda pricing.
    llm_model_prices: dict[str, tuple[float, float]] = Field(
        default_factory=lambda: {
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4o":      (0.0025, 0.01),
            "gpt-4-turbo": (0.01, 0.03),
        }
    )
```

---

## Fluxo de Dados

```
Orquestrador (M4)
    │
    ├── intelligence.reset_for_new_execution(settings)
    │       └── CostTracker novo zerado
    │
    ├── intelligence.validate(extracted_data, MeuSchema)
    │       ├── pydantic validation
    │       └── ValidationResult(is_valid, model, errors, warnings)
    │              │
    │              └── is_valid=False ──┐
    │                                    │
    ├── intelligence.call_llm(...)  ←── (só se is_valid=True E rotina precisa de LLM)
    │       ├── prompts.load("name") → Prompt
    │       ├── prompts.render(prompt, params) → str
    │       ├── cost_tracker.check_before(estimated_tokens)  → TokenBudgetExceededError?
    │       ├── _send_request(...)  ← tenacity 4x em 429/5xx
    │       │       └── LLMUnavailableError | LLMRequestError
    │       ├── response_model.model_validate_json(...) ← retry 2x se schema-mismatch
    │       │       └── LLMResponseSchemaError
    │       ├── cost_tracker.add_after(model, usage)
    │       │       └── warning em USD se > threshold (log, não bloqueia)
    │       └── LLMResult
    │              │
    │              ▼
    ├── intelligence.decide(validation, llm_result, min_confidence=settings.llm_min_confidence)
    │       └── Decision(action, reason, evidence, confidence)
    │              │
    │              ▼
    └── Switch:
        ├── PROCEED_TO_WEB    → web.fill_form(...)
        ├── ABORT_IN_DESKTOP  → log + retorno graceful
        └── RAISE_EXCEPTION   → propaga IntelligenceError customizada
```

---

## Mocks de Teste

Padrão: nunca toca OpenAI real, nunca toca filesystem em produção (usa `tmp_path`).

### Mock do cliente OpenAI

```python
from unittest.mock import MagicMock, patch
import pytest

@pytest.fixture
def mock_openai_response():
    """Resposta padrão da API com JSON válido."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = '{"decision": "approve", "confidence": 0.9}'
    response.usage.prompt_tokens = 100
    response.usage.completion_tokens = 20
    response.usage.total_tokens = 120
    return response

@pytest.fixture
def mock_openai_client(mock_openai_response):
    client = MagicMock()
    client.chat.completions.create.return_value = mock_openai_response
    with patch("intelligence.llm._get_client", return_value=client):
        yield client
```

### Mock de prompt

```python
@pytest.fixture
def sample_prompt_file(tmp_path: Path) -> Path:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    p = prompts_dir / "classify.md"
    p.write_text(
        "---\n"
        "version: 1.0.0\n"
        "model: gpt-4o-mini\n"
        "temperature: 0.0\n"
        "response_schema: TestClassification\n"
        "---\n"
        "Classifique: {input}",
        encoding="utf-8",
    )
    return prompts_dir
```

### Cenários de retry

`tenacity` aceita `sleep=` para substituir `time.sleep` em testes — passar `sleep=lambda *_: None` deixa o teste rodar em ms em vez de segundos.

```python
def test_retry_on_5xx(monkeypatch):
    call_count = {"n": 0}
    def flaky(*a, **kw):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise openai.APIStatusError("500", response=MagicMock(status_code=500), body=None)
        return _success_response()
    monkeypatch.setattr("intelligence.llm._send_request.retry.sleep", lambda *_: None)
    # ... assert _send_request foi chamado 3x
```

### Cenário de sanitização

```python
def test_log_does_not_leak_prompt_content(caplog, mock_openai_client, sample_prompt_file):
    call_llm("classify", {"input": "DADOS SENSIVEIS"}, None, settings)
    for record in caplog.records:
        assert "DADOS SENSIVEIS" not in record.getMessage()
        assert "DADOS SENSIVEIS" not in str(record.__dict__)
```

---

## Notas de Implementação

- **Pyyaml**: confirmar se já vem transitivamente via `pydantic-settings`; se não, adicionar `pyyaml` como dep direta no `pyproject.toml` e `pyyaml.*` em `ignore_missing_imports` do mypy se stubs não estiverem disponíveis.
- **Lazy import de `openai`**: dentro de `_get_client()` para evitar custo em rotinas que só usam `validate()`.
- **Lazy import de `pandas` em `analysis.py`**: idem — `analysis.py` é importado só quando o caller pede explicitamente.
- **`response_format={"type": "json_object"}`**: força a OpenAI a retornar JSON válido, reduzindo falhas de schema. Requer que o prompt mencione "responda em JSON" (validado em runtime pelo SDK).
- **`Decision.evidence` com `Decimal`/`datetime`**: usar Pydantic v2 com `model_dump(mode="json")` para serialização correta — `mode="json"` converte tipos automaticamente.
- **Reset de cost tracker**: orquestrador deve chamar `reset_for_new_execution()` no início de CADA rotina. Sem isso, custos de runs anteriores acumulam (no caso de o processo Python ficar vivo entre runs — não é o caso v1, mas defensivo).
- **Thread-safety**: cliente + tracker são globais de módulo. Documentado em `llm.py` que isso é seguro porque o orquestrador v1 é single-thread (decisão STATE 2026-05-28). Se M4 introduzir threading, refatorar para context manager.
- **Schemas de rotinas (M5)**: vivem em `intelligence/schemas/<rotina>.py`, decorados com `@register("nome")`. Não fazem parte do M3 — M3 entrega a infraestrutura.
