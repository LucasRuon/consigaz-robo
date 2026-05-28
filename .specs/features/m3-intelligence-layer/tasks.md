# M3 — Camada de Inteligência: Tasks

**Spec**: `.specs/features/m3-intelligence-layer/spec.md`
**Design**: `.specs/features/m3-intelligence-layer/design.md`
**Status**: Draft

> Gate rápido (por módulo): `pytest tests/intelligence/test_<módulo>.py -v`
> Gate completo: `pytest && ruff check src/intelligence/ && mypy src/intelligence/`

---

## Execution Plan

```
Phase 1 (Sequential — Foundation):
  T1 → T2 → T3

Phase 2 (Parallel — building blocks):
  T3 complete, then:
    ├── T4 [P]   validation.py + tests
    ├── T5 [P]   analysis.py + tests
    └── T6 [P]   schemas/__init__.py registry + tests

Phase 3 (Sequential — Prompts & LLM):
  T6 complete → T7   prompts.py + tests
  T7 complete → T8   llm.py + CostTracker + tests

Phase 4 (Parallel — Router):
  T3 complete (em paralelo com Phase 3) → T9   router.py + tests

Phase 5 (Sequential — Exports + Gate Final):
  T4 + T5 + T6 + T7 + T8 + T9 complete → T10
```

```
T1 → T2 → T3 ─┬─ T4 [P] ──────────────┐
                ├─ T5 [P] ──────────────┤
                ├─ T6 [P] ── T7 ── T8 ──┤
                └─ T9 [P] ──────────────┴── T10
```

`T9` depende apenas de `T3` (types). Pode rodar em paralelo com `T6→T7→T8` (o caminho mais longo).

---

## Task Breakdown

### T1: Scaffold do pacote `intelligence` + deps + settings novos

**What**: Criar estrutura de diretórios e `__init__.py` do pacote `intelligence`; adicionar deps (`openai`, `tenacity`, `pyyaml` se não estiver transitivamente); registrar `src/intelligence` em `pyproject.toml`; adicionar overrides de mypy para libs sem stubs; estender `config/settings.py` com os campos M3; criar diretório `config/prompts/` (vazio, alimentado em M5).

**Where**:
- `src/intelligence/__init__.py` (novo, vazio por ora — exports vêm em T10)
- `src/intelligence/schemas/__init__.py` (novo, esqueleto vazio)
- `tests/intelligence/__init__.py` (novo, vazio)
- `tests/intelligence/fixtures/prompts/` (novo diretório, vazio)
- `config/prompts/` (novo diretório, vazio)
- `pyproject.toml` (modificar): adicionar `src/intelligence` em `packages`; adicionar deps; adicionar overrides mypy (`openai.*`, `pandas.*`, `yaml.*` conforme necessário)
- `src/config/settings.py` (modificar): adicionar campos M3 conforme design (`openai_api_key`, `llm_default_model`, `llm_default_temperature`, `llm_min_confidence`, `llm_token_hard_cap`, `llm_cost_warning_usd`, `llm_prompts_dir`, `llm_model_prices`)

**Depends on**: Nenhuma
**Reuses**: Padrão de scaffold de T1 do M1/M2; `pydantic-settings` já em uso em `settings.py`
**Requirement**: INT-13 (token cap setting), INT-14 (cost warning setting), INT-16 (api key setting), INT-18 (prompts dir setting), INT-28 (min confidence setting)

**Verificação de deps a fazer ANTES de editar**:
1. `uv pip list | grep -E "openai|tenacity|pyyaml|pandas"` — `tenacity` e `pandas` provavelmente já estão (PRD); `openai` e `pyyaml` quase certamente faltam.
2. `pyyaml` pode vir transitivamente. Se já vem, não adicionar como dep direta — apenas adicionar override de mypy.

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `src/intelligence/__init__.py` existe (vazio)
- [ ] `src/intelligence/schemas/__init__.py` existe (esqueleto vazio)
- [ ] `tests/intelligence/__init__.py` existe (vazio)
- [ ] `config/prompts/` existe na raiz do projeto
- [ ] `pyproject.toml`: `src/intelligence` adicionado em `[tool.hatch.build.targets.wheel] packages`
- [ ] `pyproject.toml`: `openai` adicionado em `dependencies`
- [ ] `pyproject.toml`: `pyyaml` adicionado em `dependencies` SE não vier transitivamente
- [ ] `pyproject.toml`: overrides mypy para `openai.*` (e `pandas.*`, `yaml.*` se necessário)
- [ ] `uv sync` roda sem erro
- [ ] `settings.py`: 8 campos M3 adicionados com defaults do design
- [ ] Gate check: `python -c "import intelligence; from config.settings import Settings; s = Settings(); print(s.llm_default_model)"` retorna `gpt-4o-mini`

**Tests**: none (smoke via gate)
**Gate**: quick (`python -c "import intelligence" && uv run pytest tests/config/ -v` para revalidar settings)

**Commit**: `feat(intelligence): scaffold pacote + deps openai/pyyaml + settings M3`

---

### T2: `intelligence/exceptions.py` — hierarquia de exceções

**What**: Criar `src/intelligence/exceptions.py` com a hierarquia `IntelligenceError` completa (12 exceções); criar `tests/intelligence/test_exceptions.py`.

**Where**:
- `src/intelligence/exceptions.py` (novo)
- `tests/intelligence/test_exceptions.py` (novo)

**Depends on**: T1
**Reuses**: Padrão de `src/web/exceptions.py` e `src/desktop/exceptions.py` — atributos tipados, base `RuntimeError`
**Requirement**: INT-06, INT-09, INT-10, INT-12, INT-13, INT-16, INT-19, INT-22, INT-23, INT-29 + base IntelligenceError + SchemaNotRegisteredError

**Exceções a criar** (conforme design.md):

```python
class IntelligenceError(RuntimeError): ...

class ValidationCodeError(IntelligenceError):
    def __init__(self, schema: str, original_exception: BaseException): ...

class PromptError(IntelligenceError): ...
class PromptNotFoundError(PromptError):
    def __init__(self, name: str, path: Path): ...
class PromptMetadataError(PromptError):
    def __init__(self, name: str, reason: str): ...
class PromptRenderError(PromptError):
    def __init__(self, name: str, missing: list[str]): ...
class PromptNameError(PromptError):
    def __init__(self, name: str): ...

class LLMError(IntelligenceError): ...
class LLMConfigError(LLMError): ...
class LLMUnavailableError(LLMError):
    def __init__(self, last_exception: BaseException): ...
class LLMRequestError(LLMError):
    def __init__(self, status_code: int, message: str): ...
class LLMResponseSchemaError(LLMError):
    def __init__(self, raw_response: str, validation_errors: list[str]): ...
class TokenBudgetExceededError(LLMError):
    def __init__(self, tokens_used: int, tokens_pending: int, cap: int): ...

class RouterContractError(IntelligenceError):
    def __init__(self, expected_field: str, got_type: str): ...

class SchemaNotRegisteredError(IntelligenceError):
    def __init__(self, name: str, known: list[str]): ...
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Todas as classes definidas; hierarquia correta (PromptError/LLMError como agrupadores)
- [ ] Todas as exceções concretas são subclasses (indireta) de `IntelligenceError` que é subclasse de `RuntimeError`
- [ ] Atributos corretos em cada exceção conforme design
- [ ] `LLMResponseSchemaError.raw_response` é sanitizado ANTES de virar `str(exc)` (truncar em 200 chars + adicionar `[SANITIZED]`) — defesa em profundidade contra leak em traceback
- [ ] Gate check: `pytest tests/intelligence/test_exceptions.py -v` → todos passam
- [ ] Test count: ≥ 15 testes (issubclass, instanciação, atributos, hierarquia, sanitização do raw_response)

**Tests**: unit
**Gate**: quick (`pytest tests/intelligence/test_exceptions.py -v`)

**Commit**: `feat(intelligence): hierarquia IntelligenceError (12 exceções)`

---

### T3: `intelligence/types.py` — Action, ValidationResult, LLMResult, Decision

**What**: Criar `src/intelligence/types.py` com os 4 modelos de dados públicos do módulo; criar `tests/intelligence/test_types.py`.

**Where**:
- `src/intelligence/types.py` (novo)
- `tests/intelligence/test_types.py` (novo)

**Depends on**: T2
**Reuses**: Padrão de modelos Pydantic v2 já usados em `src/config/settings.py`
**Requirement**: INT-01 (ValidationResult), INT-07 (LLMResult), INT-24/INT-30 (Decision com confidence), GA-02

**Tipos a criar** (conforme design.md):

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
    model_instance: BaseModel | str
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

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Os 4 tipos definidos exatamente como no design
- [ ] `Decision.confidence` rejeita `< 0` e `> 1` (validador Pydantic)
- [ ] `Decision.model_dump(mode="json")` serializa `Decimal`, `datetime` corretamente (testar explicitamente com `evidence={"valor": Decimal("1.50"), "quando": datetime.now()}`)
- [ ] `Action(str, Enum)` permite comparação direta com strings (`Action.PROCEED_TO_WEB == "proceed_to_web"`)
- [ ] Gate check: `pytest tests/intelligence/test_types.py -v` → todos passam
- [ ] Test count: ≥ 8 testes (instanciação dos 4 tipos, range de confidence, serialização Decimal/datetime, Action == str, defaults)

**Tests**: unit
**Gate**: quick (`pytest tests/intelligence/test_types.py -v`)

**Commit**: `feat(intelligence): types Action/ValidationResult/LLMResult/Decision`

---

### T4: `intelligence/validation.py` — validate() com Pydantic [P]

**What**: Criar `src/intelligence/validation.py` com `validate(data, schema) → ValidationResult`; tratamento de `data=None`, erros de Pydantic ValidationError formatados como strings, separação entre erro de dado e bug de validador (`ValidationCodeError`); criar `tests/intelligence/test_validation.py` com schemas de exemplo locais.

**Where**:
- `src/intelligence/validation.py` (novo)
- `tests/intelligence/test_validation.py` (novo)

**Depends on**: T3 (usa `ValidationResult`)
**Reuses**: Pydantic v2 — `BaseModel.model_validate`, `ValidationError.errors()`
**Requirement**: INT-01, INT-02, INT-03, INT-06 (+ edge case `data=None`)

**Assinatura**:
```python
def validate(
    data: dict[str, Any] | None,
    schema: type[BaseModel],
) -> ValidationResult:
    if data is None:
        return ValidationResult(is_valid=False, errors=["payload vazio"])
    try:
        instance = schema.model_validate(data)
    except pydantic.ValidationError as e:
        errors = [
            f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
            for err in e.errors()
        ]
        return ValidationResult(is_valid=False, errors=errors)
    except Exception as e:
        raise ValidationCodeError(schema=schema.__name__, original_exception=e) from e
    return ValidationResult(is_valid=True, model=instance)
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `validate(None, AnySchema)` retorna `is_valid=False` com `errors=["payload vazio"]`
- [ ] `validate({...}, schema)` válido retorna `is_valid=True` com `.model` populado
- [ ] Erro de campo obrigatório ausente vira string `"campo: ..."` em `errors`
- [ ] Schema com `extra="forbid"` rejeita dict com chaves extras
- [ ] Bug em validador customizado (ex: TypeError) vira `ValidationCodeError` (não vaza)
- [ ] Gate check: `pytest tests/intelligence/test_validation.py -v` → todos passam
- [ ] Test count: ≥ 10 testes (válido, data=None, campo faltando, tipo errado, extra forbid, range Pydantic Field(ge=0), ValidationCodeError, formato da mensagem de erro)

**Tests**: unit
**Gate**: quick (`pytest tests/intelligence/test_validation.py -v`)

**Commit**: `feat(intelligence): validate(data, schema) → ValidationResult com Pydantic`

---

### T5: `intelligence/analysis.py` — helpers Pandas [P]

**What**: Criar `src/intelligence/analysis.py` com `validate_range()` e `compare_against_history()`; criar `tests/intelligence/test_analysis.py`; **lazy import de pandas** dentro das funções para não pagar custo de import quando não usado.

**Where**:
- `src/intelligence/analysis.py` (novo)
- `tests/intelligence/test_analysis.py` (novo)

**Depends on**: T2 (não usa types, mas precisa do scaffold + deps)
**Reuses**: Padrão de lazy import já registrado no STATE.md (lição 2026-05-28 sobre adapters de plataforma)
**Requirement**: INT-04, INT-05

**Assinaturas**:
```python
def validate_range(
    value: float | Decimal,
    lo: float | Decimal,
    hi: float | Decimal,
    field_name: str = "valor",
) -> str | None:
    if value < lo:
        return f"{field_name} ({value}) menor que mínimo ({lo})"
    if value > hi:
        return f"{field_name} ({value}) maior que máximo ({hi})"
    return None

def compare_against_history(
    value: float,
    series: "pd.Series",  # forward ref para evitar import top-level
    threshold_std: float = 2.0,
) -> bool:
    import pandas as pd  # lazy
    if len(series) == 0:
        return True  # sem histórico → não há base para reprovar
    mean = float(series.mean())
    std = float(series.std()) if len(series) > 1 else 0.0
    if std == 0:
        return value == mean
    return abs(value - mean) <= threshold_std * std
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `pandas` é importado SOMENTE dentro de `compare_against_history()`, não no topo do arquivo
- [ ] `validate_range(5, 0, 10)` retorna `None`; `validate_range(-1, 0, 10)` retorna string com "menor que mínimo"; `validate_range(11, 0, 10)` retorna string com "maior que máximo"
- [ ] `compare_against_history()` com série vazia retorna `True` (defensivo)
- [ ] `compare_against_history()` com série de 1 elemento (std=0) usa igualdade
- [ ] `compare_against_history()` aceita Decimal sem crash (converte internamente)
- [ ] Gate check: `pytest tests/intelligence/test_analysis.py -v` → todos passam
- [ ] Confirmar que `import intelligence.validation` (sem chamar `analysis`) não importa pandas — verificar via `sys.modules` em teste isolado
- [ ] Test count: ≥ 8 testes

**Tests**: unit
**Gate**: quick (`pytest tests/intelligence/test_analysis.py -v`)

**Commit**: `feat(intelligence): analysis.py com validate_range + compare_against_history (lazy pandas)`

---

### T6: `intelligence/schemas/__init__.py` — registry [P]

**What**: Implementar registry de schemas de resposta da LLM em `src/intelligence/schemas/__init__.py`; decorador `@register(name)` + `get_schema(name) → type[BaseModel]`; criar `tests/intelligence/test_schemas_registry.py`.

**Where**:
- `src/intelligence/schemas/__init__.py` (já criado em T1 como esqueleto — agora implementa)
- `tests/intelligence/test_schemas_registry.py` (novo)

**Depends on**: T2 (usa `SchemaNotRegisteredError`)
**Reuses**: Padrão clássico de plugin registry
**Requirement**: GA-04 (schemas referenciáveis por nome no frontmatter dos prompts)

**Implementação**:
```python
from pydantic import BaseModel
from intelligence.exceptions import SchemaNotRegisteredError

_REGISTRY: dict[str, type[BaseModel]] = {}

def register(name: str):
    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        if name in _REGISTRY and _REGISTRY[name] is not cls:
            raise RuntimeError(f"schema '{name}' já registrado para outra classe")
        _REGISTRY[name] = cls
        return cls
    return decorator

def get_schema(name: str) -> type[BaseModel]:
    if name not in _REGISTRY:
        raise SchemaNotRegisteredError(name=name, known=sorted(_REGISTRY))
    return _REGISTRY[name]

def list_schemas() -> list[str]:
    return sorted(_REGISTRY)

def _clear_registry_for_tests() -> None:
    """Usado pelas fixtures de teste para isolar registros entre testes."""
    _REGISTRY.clear()
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `@register("foo")` em uma classe Pydantic adiciona ao registry
- [ ] `get_schema("foo")` retorna a classe registrada
- [ ] `get_schema("inexistente")` lança `SchemaNotRegisteredError` com `.name` e `.known`
- [ ] Re-registrar a mesma classe com mesmo nome é no-op (não lança)
- [ ] Re-registrar nome com classe diferente lança RuntimeError
- [ ] `list_schemas()` retorna ordem estável (sorted)
- [ ] Fixture `clear_schema_registry` em `conftest.py` limpa entre testes
- [ ] Gate check: `pytest tests/intelligence/test_schemas_registry.py -v` → todos passam
- [ ] Test count: ≥ 8 testes

**Tests**: unit
**Gate**: quick (`pytest tests/intelligence/test_schemas_registry.py -v`)

**Commit**: `feat(intelligence): registry de schemas com @register / get_schema`

---

### T7: `intelligence/prompts.py` — load + render com frontmatter

**What**: Criar `src/intelligence/prompts.py` com `Prompt` (dataclass frozen), `load(name) → Prompt`, `render(prompt, params) → str`; parser de frontmatter YAML inline (sem dep `python-frontmatter`); validação de traversal em `name`; validação de `version` obrigatória; validação de `response_schema` no registry (chamada de `get_schema` na load); criar `tests/intelligence/test_prompts.py` + fixtures `.md` em `tests/intelligence/fixtures/prompts/`.

**Where**:
- `src/intelligence/prompts.py` (novo)
- `tests/intelligence/test_prompts.py` (novo)
- `tests/intelligence/fixtures/prompts/valid.md` (novo)
- `tests/intelligence/fixtures/prompts/missing_version.md` (novo)
- `tests/intelligence/fixtures/prompts/no_frontmatter.md` (novo)
- `tests/intelligence/fixtures/prompts/malformed_yaml.md` (novo)

**Depends on**: T6 (usa `get_schema` para validar `response_schema`)
**Reuses**: `pyyaml` adicionado em T1; padrão `Path(__file__).parent...` para resolver `config/prompts/` default
**Requirement**: INT-18, INT-19, INT-20, INT-21, INT-22, INT-23, GA-04

**Implementação** (conforme design.md):

```python
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml

from intelligence.exceptions import (
    PromptNotFoundError, PromptMetadataError,
    PromptRenderError, PromptNameError,
)
from intelligence.schemas import get_schema  # valida cedo

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_PROMPTS_DIR = _PROJECT_ROOT / "config" / "prompts"


@dataclass(frozen=True)
class Prompt:
    name: str
    template: str
    version: str
    model: str | None
    temperature: float | None
    response_schema: str | None


class _Placeholders(dict):
    def __init__(self, params: dict[str, Any]):
        super().__init__(params)
        self.missing: list[str] = []
    def __missing__(self, key):
        self.missing.append(key)
        return "{" + key + "}"


def load(name: str, prompts_dir: Path | None = None) -> Prompt:
    if not name or "/" in name or "\\" in name or ".." in name:
        raise PromptNameError(name=name)
    base = prompts_dir or _DEFAULT_PROMPTS_DIR
    path = base / f"{name}.md"
    if not path.exists():
        raise PromptNotFoundError(name=name, path=path)
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise PromptMetadataError(name=name, reason="frontmatter ausente ou malformado")
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        raise PromptMetadataError(name=name, reason=str(e)) from e
    if "version" not in meta:
        raise PromptMetadataError(name=name, reason="campo 'version' obrigatório")
    response_schema = meta.get("response_schema")
    if response_schema is not None:
        # Valida cedo — falha no load, não no call_llm
        get_schema(response_schema)
    return Prompt(
        name=name,
        template=match.group(2),
        version=str(meta["version"]),
        model=meta.get("model"),
        temperature=meta.get("temperature"),
        response_schema=response_schema,
    )


def render(prompt: Prompt, params: dict[str, Any]) -> str:
    holder = _Placeholders(params)
    rendered = prompt.template.format_map(holder)
    if holder.missing:
        raise PromptRenderError(name=prompt.name, missing=holder.missing)
    return rendered
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `load("valid")` carrega prompt com todos os campos do frontmatter
- [ ] `load("/etc/passwd")` lança `PromptNameError`
- [ ] `load("../escape")` lança `PromptNameError`
- [ ] `load("inexistente")` lança `PromptNotFoundError` com `.path` completo
- [ ] `load("no_frontmatter")` lança `PromptMetadataError`
- [ ] `load("malformed_yaml")` lança `PromptMetadataError` com `.reason` do parser YAML
- [ ] `load("missing_version")` lança `PromptMetadataError`
- [ ] `load("with_unknown_schema")` lança `SchemaNotRegisteredError` (validação cedo)
- [ ] `load()` aplica defaults: `model=None`, `temperature=None` quando omitidos (caller resolve com settings)
- [ ] `render(prompt, {"x": "y"})` substitui `{x}` por `y`
- [ ] `render(prompt, {})` em template `Olá {nome}` lança `PromptRenderError(missing=["nome"])`
- [ ] `render(prompt, {"nome": "X", "extra": "ignorado"})` ignora chave extra (sem erro)
- [ ] Gate check: `pytest tests/intelligence/test_prompts.py -v` → todos passam
- [ ] Test count: ≥ 15 testes

**Tests**: unit
**Gate**: quick (`pytest tests/intelligence/test_prompts.py -v`)

**Commit**: `feat(intelligence): prompts.load + render com frontmatter YAML`

---

### T8: `intelligence/llm.py` — cliente OpenAI + CostTracker + retry

**What**: Criar `src/intelligence/llm.py` com `_get_client()` (lazy), `CostTracker` (dataclass), `reset_for_new_execution()`, `call_llm(prompt_name, params, response_model, settings) → LLMResult`. Implementar retry exponencial via `tenacity` para 429/5xx; retry separado em schema-mismatch (até 2x não-exponencial); guard rail de tokens ANTES da chamada; warning de USD APÓS chamada (log estruturado); sanitização: nenhum prompt/response cru no log. Criar `tests/intelligence/test_llm.py` com mocks via `monkeypatch` em `openai.OpenAI`.

**Where**:
- `src/intelligence/llm.py` (novo)
- `tests/intelligence/test_llm.py` (novo)
- `tests/intelligence/conftest.py` (novo ou modificado — fixtures `mock_openai_client`, `reset_llm_state`)

**Depends on**: T3 (LLMResult), T7 (prompts), T2 (exceções)
**Reuses**: `tenacity` (já em uso em retry HTTP do PRD); padrão de cliente lazy do projeto; sanitização do logger já implementada em M0
**Requirement**: INT-07 a INT-17

**Estrutura do arquivo** (esboço — consulte design.md para detalhes completos):

```python
import time
from dataclasses import dataclass, field
from typing import Any

import openai
from tenacity import (
    retry, wait_exponential, stop_after_attempt,
    retry_if_exception, RetryError,
)
from pydantic import BaseModel, ValidationError as PydanticValidationError

from config.settings import Settings
from intelligence import secrets  # ou onde estiver o wrapper de keyring
from intelligence.exceptions import (
    LLMConfigError, LLMUnavailableError, LLMRequestError,
    LLMResponseSchemaError, TokenBudgetExceededError,
)
from intelligence.prompts import load as load_prompt, render as render_prompt
from intelligence.types import LLMResult
from logger import get_logger  # logger estruturado do M0

log = get_logger(__name__)

_client: openai.OpenAI | None = None
_cost_tracker: "CostTracker | None" = None


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
            raise TokenBudgetExceededError(
                tokens_used=self.tokens_used,
                tokens_pending=estimated_tokens,
                cap=self.token_hard_cap,
            )

    def add_after(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        self.tokens_used += prompt_tokens + completion_tokens
        price_in, price_out = self.model_prices.get(model, (0.0, 0.0))
        cost = (prompt_tokens * price_in + completion_tokens * price_out) / 1000
        self.cost_usd += cost
        if self.cost_usd > self.cost_warning_usd and not self.warning_emitted:
            log.warning("llm_cost_warning", extra={
                "cost_usd_accumulated": self.cost_usd,
                "cost_warning_threshold_usd": self.cost_warning_usd,
            })
            self.warning_emitted = True
        return cost


def _get_client(settings: Settings) -> openai.OpenAI:
    global _client
    if _client is None:
        api_key = None
        try:
            from config import secrets as _secrets  # adapt to actual location
            api_key = _secrets.get("OPENAI_API_KEY")
        except Exception:
            pass
        if not api_key and settings.openai_api_key:
            api_key = settings.openai_api_key.get_secret_value()
        if not api_key:
            raise LLMConfigError("OPENAI_API_KEY ausente em keyring e .env")
        _client = openai.OpenAI(api_key=api_key)
    return _client


def reset_for_new_execution(settings: Settings) -> None:
    global _cost_tracker
    _cost_tracker = CostTracker(
        token_hard_cap=settings.llm_token_hard_cap,
        cost_warning_usd=settings.llm_cost_warning_usd,
        model_prices=dict(settings.llm_model_prices),
    )


def _get_tracker() -> "CostTracker":
    if _cost_tracker is None:
        raise LLMConfigError("reset_for_new_execution() não foi chamado")
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
def _send_request(client, model, messages, temperature):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )


def call_llm(
    prompt_name: str,
    params: dict[str, Any],
    response_model: type[BaseModel] | None,
    settings: Settings,
) -> LLMResult:
    prompt = load_prompt(prompt_name, settings.llm_prompts_dir)
    rendered = render_prompt(prompt, params)
    model = prompt.model or settings.llm_default_model
    temperature = prompt.temperature if prompt.temperature is not None else settings.llm_default_temperature
    tracker = _get_tracker()

    # estimativa conservadora: 1 token ~= 4 chars; só pra check_before
    estimated_tokens = max(1, len(rendered) // 4) + 500  # buffer para resposta
    tracker.check_before(estimated_tokens)

    client = _get_client(settings)
    messages = [{"role": "user", "content": rendered}]

    raw_content = None
    for attempt in range(3):
        try:
            t0 = time.perf_counter()
            response = _send_request(client, model, messages, temperature)
        except openai.RateLimitError as e:
            raise LLMUnavailableError(last_exception=e) from e
        except openai.APIStatusError as e:
            if 500 <= e.status_code < 600:
                raise LLMUnavailableError(last_exception=e) from e
            raise LLMRequestError(status_code=e.status_code, message=str(e)) from e
        except RetryError as e:  # esgotou retries do tenacity
            raise LLMUnavailableError(last_exception=e) from e

        latency_ms = int((time.perf_counter() - t0) * 1000)
        raw_content = response.choices[0].message.content or ""

        if response_model is None:
            instance: BaseModel | str = raw_content
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
            continue  # retentar imediatamente

    usage = response.usage
    cost = tracker.add_after(model, usage.prompt_tokens, usage.completion_tokens)

    log.info("llm_call", extra={
        "prompt_name": prompt.name,
        "prompt_version": prompt.version,
        "model": model,
        "tokens_in": usage.prompt_tokens,
        "tokens_out": usage.completion_tokens,
        "cost_usd_estimate": cost,
        "latency_ms": latency_ms,
        # PROIBIDO: prompt_text, response_text, params
    })

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
```

**Tools**:
- MCP: context7 (`mcp__context7__query-docs`) — opcional, para confirmar API atual do `openai-python` SDK (model_validate_json vs parse) caso versão instalada divirja
- Skill: NONE

**Done when**:
- [ ] `_get_client()` lança `LLMConfigError` se nem keyring nem `.env` têm chave
- [ ] `reset_for_new_execution()` zera tokens e cost; chamadas subsequentes a `call_llm` acumulam no tracker novo
- [ ] `call_llm` sem `reset_for_new_execution` prévio lança `LLMConfigError`
- [ ] Mock de 429 N vezes seguido de sucesso → retry até 4x e retorna LLMResult (com `sleep` mockado)
- [ ] Mock de 500 N vezes → `LLMUnavailableError` após esgotar retries
- [ ] Mock de 400 → `LLMRequestError` SEM retry
- [ ] Mock que retorna JSON com schema errado 3x → `LLMResponseSchemaError`
- [ ] Mock que retorna JSON com schema errado 1x e ok 2x → sucesso na 3ª tentativa
- [ ] Hard cap em tokens estourado → `TokenBudgetExceededError` ANTES da chamada (mock confirma que `client.chat.completions.create` nunca foi chamado)
- [ ] Custo acumulado > `cost_warning_usd` → log com `level=WARNING` E key `llm_cost_warning` (capturado via `caplog`); subsequente NÃO loga de novo
- [ ] Teste de sanitização: prompt com `params={"x": "DADOS_SENSIVEIS_XYZ"}` → nenhum record em `caplog` contém a string em qualquer campo
- [ ] `response_model=None` → `LLMResult.model_instance` é `str` com resposta crua
- [ ] Gate check: `pytest tests/intelligence/test_llm.py -v` → todos passam
- [ ] Test count: ≥ 20 testes

**Tests**: unit
**Gate**: quick (`pytest tests/intelligence/test_llm.py -v`)

**Commit**: `feat(intelligence): cliente OpenAI com retry, CostTracker, response_model tipado`

---

### T9: `intelligence/router.py` — decide() pura [P com Phase 3]

**What**: Criar `src/intelligence/router.py` com a função `decide(validation, llm_result, *, min_confidence=0.7) → Decision` conforme design; mapeamento `approve/reject/escalate` → `Action`; validação de contrato (`hasattr(instance, "decision")`); criar `tests/intelligence/test_router.py` table-driven cobrindo a matriz completa.

**Where**:
- `src/intelligence/router.py` (novo)
- `tests/intelligence/test_router.py` (novo)

**Depends on**: T3 (Action, Decision, ValidationResult, LLMResult), T2 (RouterContractError)
**Reuses**: Tipos do T3
**Requirement**: INT-24 a INT-30

**Implementação completa em `design.md` (Decisões Arquiteturais → Router)**.

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `decide(validation=invalid, llm=None)` → `Action.ABORT_IN_DESKTOP`, `confidence=1.0`, `evidence={"errors": [...]}`
- [ ] `decide(validation=valid, llm=None)` → `Action.PROCEED_TO_WEB`, `confidence=1.0`
- [ ] `decide(validation=valid, llm.decision="approve", llm.confidence=0.9)` → `PROCEED_TO_WEB`
- [ ] `decide(..., llm.decision="reject")` → `ABORT_IN_DESKTOP`
- [ ] `decide(..., llm.decision="escalate")` → `RAISE_EXCEPTION`
- [ ] `decide(..., llm.confidence=0.5)` (< default 0.7) → `RAISE_EXCEPTION` independente de `llm.decision`
- [ ] `decide(..., min_confidence=0.3, llm.confidence=0.5)` → respeita override do caller
- [ ] LLM result sem atributo `.decision` → `RouterContractError(expected_field="decision")`
- [ ] LLM result com `.decision="approve"` mas sem `.confidence` → assume `confidence=1.0`
- [ ] **Teste de pureza**: chamar `decide()` 100x com mesmo input dá output deterministicamente igual (compara via `model_dump`)
- [ ] **Teste de sem-mutação**: `validation` e `llm_result` são iguais ANTES e DEPOIS de `decide()` (deep equal)
- [ ] `Decision.evidence` com `Decimal` → `model_dump(mode="json")` serializa OK
- [ ] Gate check: `pytest tests/intelligence/test_router.py -v` → todos passam
- [ ] Test count: ≥ 15 testes (table-driven em uma `parametrize` + testes de pureza)

**Tests**: unit
**Gate**: quick (`pytest tests/intelligence/test_router.py -v`)

**Commit**: `feat(intelligence): router.decide() puro com confidence + RouterContractError`

---

### T10: Exports públicos + gate final

**What**: Popular `src/intelligence/__init__.py` com os exports públicos do módulo (API que o orquestrador consome); rodar gate completo (`pytest && ruff check src/intelligence/ && mypy src/intelligence/`); documentar API pública no docstring do `__init__.py`.

**Where**:
- `src/intelligence/__init__.py` (modificar — adicionar exports)

**Depends on**: T4, T5, T6, T7, T8, T9
**Reuses**: Padrão de `src/web/__init__.py` para exports
**Requirement**: cobertura final dos 30 INT-*

**Exports** (API pública do módulo):

```python
"""
intelligence — camada determinística + LLM entre desktop/ e web/.

API pública:
    validate(data, schema) -> ValidationResult
    call_llm(prompt_name, params, response_model, settings) -> LLMResult
    decide(validation, llm_result, *, min_confidence) -> Decision
    reset_for_new_execution(settings) -> None

Tipos:
    Action, ValidationResult, LLMResult, Decision, Prompt

Exceções:
    IntelligenceError (base), ValidationCodeError,
    PromptError + subclasses, LLMError + subclasses,
    RouterContractError, SchemaNotRegisteredError
"""

from intelligence.types import Action, ValidationResult, LLMResult, Decision
from intelligence.validation import validate
from intelligence.llm import call_llm, reset_for_new_execution
from intelligence.router import decide
from intelligence.prompts import Prompt, load as load_prompt, render as render_prompt
from intelligence.schemas import register as register_schema, get_schema, list_schemas
from intelligence.exceptions import (
    IntelligenceError,
    ValidationCodeError,
    PromptError, PromptNotFoundError, PromptMetadataError,
    PromptRenderError, PromptNameError,
    LLMError, LLMConfigError, LLMUnavailableError,
    LLMRequestError, LLMResponseSchemaError, TokenBudgetExceededError,
    RouterContractError, SchemaNotRegisteredError,
)

__all__ = [
    # API
    "validate", "call_llm", "reset_for_new_execution", "decide",
    "load_prompt", "render_prompt",
    "register_schema", "get_schema", "list_schemas",
    # tipos
    "Action", "ValidationResult", "LLMResult", "Decision", "Prompt",
    # exceções
    "IntelligenceError", "ValidationCodeError",
    "PromptError", "PromptNotFoundError", "PromptMetadataError",
    "PromptRenderError", "PromptNameError",
    "LLMError", "LLMConfigError", "LLMUnavailableError",
    "LLMRequestError", "LLMResponseSchemaError", "TokenBudgetExceededError",
    "RouterContractError", "SchemaNotRegisteredError",
]
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `from intelligence import validate, call_llm, decide, reset_for_new_execution` funciona
- [ ] `from intelligence import Action, ValidationResult, LLMResult, Decision, Prompt` funciona
- [ ] `from intelligence import IntelligenceError` funciona (base exception acessível)
- [ ] Gate FINAL: `inv test` (ou `pytest`) passa 100% em macOS — todo o `tests/intelligence/`
- [ ] Gate FINAL: `ruff check src/intelligence/` limpo
- [ ] Gate FINAL: `mypy src/intelligence/` zero erros em modo strict
- [ ] Test count agregado de M3: ≥ 100 testes (10+15+8+10+8+8+15+20+15 = 109 estimados)
- [ ] Atualizar `ROADMAP.md`: marcar 3 features do M3 como **DONE ✅** e mudar status para "M3 concluído ✅ — pronto para M4"
- [ ] Atualizar `STATE.md`: adicionar entry de validação M3 (similar ao que existe para M0/M1/M2)

**Tests**: all
**Gate**: completo (`pytest && ruff check src/intelligence/ && mypy src/intelligence/`)

**Commit**: `feat(intelligence): exports públicos + M3 completo (109 tests passing)`

---

## Cobertura de Requisitos

| Requirement | Tasks | Status |
|---|---|---|
| INT-01 (ValidationResult) | T3, T4 | Pending |
| INT-02 (errors formatados) | T4 | Pending |
| INT-03 (extra="forbid") | T4 | Pending |
| INT-04 (validate_range) | T5 | Pending |
| INT-05 (compare_against_history) | T5 | Pending |
| INT-06 (ValidationCodeError) | T2, T4 | Pending |
| INT-07 (call_llm → LLMResult) | T3, T8 | Pending |
| INT-08 (retry exponencial 429/5xx) | T8 | Pending |
| INT-09 (LLMUnavailableError) | T2, T8 | Pending |
| INT-10 (LLMRequestError sem retry) | T2, T8 | Pending |
| INT-11 (retry schema-mismatch 2x) | T8 | Pending |
| INT-12 (LLMResponseSchemaError) | T2, T8 | Pending |
| INT-13 (TokenBudgetExceededError) | T2, T8 | Pending |
| INT-14 (warning USD) | T8 | Pending |
| INT-15 (log sanitizado) | T8 | Pending |
| INT-16 (LLMConfigError) | T2, T8 | Pending |
| INT-17 (response_model=None texto livre) | T8 | Pending |
| INT-18 (prompts.load) | T7 | Pending |
| INT-19 (Prompt errors) | T2, T7 | Pending |
| INT-20 (version obrigatória) | T7 | Pending |
| INT-21 (render `{var}`) | T7 | Pending |
| INT-22 (PromptRenderError com missing) | T2, T7 | Pending |
| INT-23 (rejeitar traversal) | T7 | Pending |
| INT-24 (decide pura) | T9 | Pending |
| INT-25 (invalid → ABORT) | T9 | Pending |
| INT-26 (valid + llm=None → PROCEED) | T9 | Pending |
| INT-27 (approve/reject/escalate map) | T9 | Pending |
| INT-28 (confidence < threshold → RAISE) | T9 | Pending |
| INT-29 (RouterContractError) | T2, T9 | Pending |
| INT-30 (Decision.model_dump JSON safe) | T3, T9 | Pending |

**Coverage**: 30/30 mapeados ✅

---

## Notas para Execução

- **Não inventar prompts reais** em M3 — `config/prompts/` fica vazio. Prompts vivem em M5 quando a rotina-piloto for definida.
- **Não criar schemas de rotina** — `intelligence/schemas/` só tem o registry. Schemas concretos vêm em M5 com `@register("nome")`.
- **Testes não tocam OpenAI real** — toda interação é mockada. CI roda sem `OPENAI_API_KEY` definido.
- **`secrets.get("OPENAI_API_KEY")`**: se o wrapper de keyring do M0 estiver em local diferente do esboçado no design (ex: `config.secrets` em vez de `intelligence.secrets`), ajustar import em T8. Verificar antes de implementar.
- **Atualizar `CLAUDE.md`** se houver convenção nova introduzida (por enquanto, não há — segue o padrão de M1/M2).
