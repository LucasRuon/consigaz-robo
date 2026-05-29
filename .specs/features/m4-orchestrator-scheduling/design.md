# M4 — Design

## Visão Arquitetural

M4 transforma o esqueleto atual de `orchestrator/` em um chassis de produção. O fluxo de uma execução agendada passa a ser:

```
cron/launchd/schtasks
        │
        ▼
python -m orchestrator --routine X [--dry-run]
        │
        ▼
┌───────────────────────────────────────────────────┐
│ cli.main()                                         │
│  ├─ parse_args                                     │
│  ├─ boot()  ──────────► BootContext (M0)           │
│  ├─ registry.discover()                            │
│  ├─ dispatch(name, ctx)                            │
│  │   ├─ intelligence.reset_for_new_execution()     │
│  │   ├─ routine(ctx) → RoutineResult               │
│  │   └─ summary.emit(result, metrics)              │
│  └─ map exception → exit code                      │
└───────────────────────────────────────────────────┘
```

Princípio orientador: **o orquestrador não conhece o domínio**. Ele inicializa, despacha e mede. Toda lógica de negócio mora dentro de uma rotina (M5+).

---

## Mapa de Módulos

```
src/orchestrator/
├── __init__.py         # exporta boot, dispatch, registry, types públicos
├── __main__.py         # python -m orchestrator → cli.main()
├── boot.py             # JÁ EXISTE — preservar assinatura
├── cli.py              # ESTENDER — --list, exit codes, dispatch
├── context.py          # NOVO — RoutineContext (frozen dataclass)
├── dispatch.py         # NOVO — dispatch(name, ctx) → RoutineResult
├── exceptions.py       # NOVO — RoutineRegistryError, RoutineNameError, UnknownRoutineError
├── registry.py         # NOVO — @register, get, list_names, discover
├── summary.py          # NOVO — emit_summary(ctx, result, metrics)
└── types.py            # NOVO — Routine, RoutineResult

src/routines/
└── __init__.py         # NOVO — auto-discovery via pkgutil

src/intelligence/
└── llm.py              # AJUSTE MÍNIMO — expor get_cost_snapshot() público

docs/
└── scheduling.md       # NOVO — receitas cron/launchd/schtasks
```

---

## Componentes Detalhados

### 1. `orchestrator/registry.py`

```python
_REGISTRY: dict[str, Routine] = {}

def register(name: str) -> Callable[[Routine], Routine]:
    """Decorator: marca função como rotina despachável."""

def get(name: str) -> Routine:
    """Retorna rotina ou lança UnknownRoutineError."""

def list_names() -> list[str]:
    """Nomes em ordem alfabética."""

def discover(package: str = "routines") -> None:
    """Importa todos os submódulos de `package` disparando os @register.
    Falha de import em uma rotina é logada e ignorada (não derruba o resto)."""
```

**Decisões:**
- Estado de módulo é OK — orquestrador é single-process, single-execution.
- `discover()` recebe `package` como parâmetro para permitir testes com pacote-fixture (`tests.fixtures.routines`).
- Validação de nome: regex `^[a-z][a-z0-9_-]*$`; tudo fora dispara `RoutineNameError`.

### 2. `orchestrator/types.py`

```python
@dataclass(frozen=True)
class RoutineResult:
    action: Action               # reusa intelligence.types.Action
    evidence: dict[str, Any]     # contexto livre p/ summary
    exit_code_hint: int | None = None

Routine = Callable[["RoutineContext"], RoutineResult]
```

`Action` (de M3) tem `PROCEED_TO_WEB`, `ABORT_IN_DESKTOP`, `RAISE_EXCEPTION`. M4 mapeia:
- `PROCEED_TO_WEB` → exit 0
- `ABORT_IN_DESKTOP` → exit 5
- `RAISE_EXCEPTION` → exit 5
- `exit_code_hint` sobrescreve quando rotina precisa de granularidade adicional.

### 3. `orchestrator/context.py`

```python
@dataclass(frozen=True)
class RoutineContext:
    platform: Platform
    settings: Settings
    logger: BoundLogger
    routine_name: str
    dry_run: bool
    started_at: datetime   # UTC tz-aware

    @classmethod
    def from_boot(cls, boot_ctx: BootContext, *, dry_run: bool) -> Self:
        ...
```

`logger` é o resultado de `get_logger(__name__).bind(routine=name)` — todo log emitido pela rotina herda a chave `routine`.

### 4. `orchestrator/dispatch.py`

```python
def dispatch(name: str, boot_ctx: BootContext, *, dry_run: bool) -> int:
    """Resolve rotina, prepara contexto, executa, emite summary, retorna exit code."""
    routine = registry.get(name)
    ctx = RoutineContext.from_boot(boot_ctx, dry_run=dry_run)
    intelligence.reset_for_new_execution(boot_ctx.settings)

    try:
        result = routine(ctx)
        exit_code = result.exit_code_hint or _exit_for_action(result.action)
        summary.emit(ctx, result=result, exit_code=exit_code)
        return exit_code
    except Exception as err:
        summary.emit_error(ctx, error=err)
        raise   # cli.main faz o mapeamento final
```

`dispatch` **propaga exceções** para `cli.main` mapear, mas garante que o summary sai antes. Esse split mantém `cli.py` como único ponto que conhece a tabela de exit codes.

### 5. `orchestrator/summary.py`

```python
def emit(ctx: RoutineContext, *, result: RoutineResult, exit_code: int) -> None:
    snap = intelligence.llm.get_cost_snapshot()   # (tokens_in, tokens_out, cost_usd)
    ctx.logger.info(
        "execution_summary",
        routine=ctx.routine_name,
        action=result.action.value,
        duration_s=round((utcnow() - ctx.started_at).total_seconds(), 3),
        tokens_in=snap.tokens_in,
        tokens_out=snap.tokens_out,
        cost_usd=round(snap.cost_usd, 4),
        exit_code=exit_code,
        dry_run=ctx.dry_run,
        started_at=ctx.started_at.isoformat(),
        finished_at=utcnow().isoformat(),
        evidence_keys=sorted(result.evidence.keys()),  # nunca o conteúdo
    )

def emit_error(ctx, *, error: BaseException) -> None: ...
def emit_boot_failure(*, routine: str, error: BaseException) -> None:
    """Fallback: stderr JSON quando logger não inicializou."""
```

**Chave de decisão:** summary expõe **nomes** de evidências, nunca valores. Conteúdo de evidence pode ter PII e já foi sanitizado em outros eventos da rotina.

### 6. `orchestrator/cli.py` (estendido)

Novo argparse:
```
--list                  # mutuamente exclusivo com --routine
--routine NAME
--dry-run               # só faz sentido com --routine
```

Tabela de exit codes implementada em uma única função `_map_exception(err) -> int`:

| Exceção                        | Exit |
|--------------------------------|------|
| (sucesso)                      | 0    |
| `KeyboardInterrupt`            | 130  |
| `pydantic.ValidationError`     | 2    |
| `UnsupportedPlatformError`     | 3    |
| `UnknownRoutineError`          | 4    |
| `RoutineRegistryError`         | 4    |
| (default — `Exception`)        | 1    |

Exit 5 vem do `dispatch` (action de rotina), não de exceção — `cli.main` só repassa o int retornado.

### 7. `routines/__init__.py`

```python
"""Pacote raiz de rotinas. Importar este módulo dispara os @register."""
from __future__ import annotations
import pkgutil, importlib, logging

log = logging.getLogger(__name__)

for _, name, _ in pkgutil.iter_modules(__path__):
    try:
        importlib.import_module(f"{__name__}.{name}")
    except Exception as err:
        log.warning("routine_import_failed", extra={"module": name, "error": str(err)})
```

**Por que assim e não eager-load no `cli`:** mantém `routines` como pacote auto-descritivo; testes podem importar `routines` diretamente sem passar pelo CLI.

### 8. `intelligence/llm.py` — ajuste mínimo

Adicionar:
```python
@dataclass(frozen=True)
class CostSnapshot:
    tokens_in: int
    tokens_out: int
    cost_usd: float

def get_cost_snapshot() -> CostSnapshot:
    """Snapshot do tracker atual. Retorna zeros se reset não foi chamado."""
```

Expor em `intelligence/__init__.py`. Sem isso, M4 acopla a internals de M3.

---

## Fluxos End-to-End

### Happy path

```
cron → python -m orchestrator --routine consigaz-pedido
  cli.main()
    boot()                                            → BootContext
    registry.discover("routines")                     → carrega N rotinas
    dispatch("consigaz-pedido", boot_ctx, dry_run=False)
      reset_for_new_execution(settings)
      ctx = RoutineContext.from_boot(...)
      result = consigaz_pedido.run(ctx)              → action=PROCEED_TO_WEB
      summary.emit(ctx, result, exit_code=0)
      return 0
    sys.exit(0)
```

### Rotina aborta (validação falhou)

```
dispatch → routine retorna RoutineResult(action=ABORT_IN_DESKTOP, evidence={...})
  exit_code = 5
  summary.emit(...) com action="ABORT_IN_DESKTOP", exit_code=5
  return 5
```

### Exceção dentro da rotina

```
dispatch → routine levanta WebInjectionError
  summary.emit_error(ctx, error)   ← action="error", error_type, error_msg
  raise
cli.main → _map_exception(WebInjectionError) → 1
sys.exit(1)
```

### Falha de boot (env var faltando)

```
cli.main → boot() levanta pydantic.ValidationError
  summary.emit_boot_failure(routine=args.routine, error=err)   ← stderr JSON
  return 2
```

---

## Auto-Discovery: por que assim

Alternativas consideradas:
1. **Entry points em `pyproject`** — flexível, mas exige reinstalar o pacote a cada nova rotina. Atrito alto durante dev.
2. **Lista manual em `cli.py`** — simples, mas força edição da CLI a cada rotina.
3. **`pkgutil.iter_modules` no pacote `routines/`** ✅ — escolhida: zero config, basta criar `routines/foo.py` com `@register("foo")`.

Limitação aceita: rotinas precisam estar em `src/routines/` (não em subpacotes aninhados). Se M5+ exigir, expandir `discover()` para `walk_packages`.

---

## Sumário: forma e custo

Decisão "linha JSON" (vinda da fase discuss) significa:
- Um único evento `execution_summary` por execução, no logger estruturado existente (M0).
- Não há novo arquivo, não há tabela, não há format string especial.
- `grep '"event":"execution_summary"' logs/*.json | jq '.cost_usd'` é o caminho de inspeção.

Tradeoff: operadores que rodam manualmente terão de olhar o `.log` humano para ver o sumário formatado — aceito, porque modo manual é desenvolvimento, não operação.

---

## Estratégia de Testes

| Camada     | Estratégia                                                                              |
|------------|------------------------------------------------------------------------------------------|
| registry   | Testes unitários com decorator aplicado a stubs; reset do `_REGISTRY` via fixture       |
| discover   | `tests/fixtures/routines/` com 2-3 módulos válidos + 1 que levanta no import            |
| context    | Construção via `from_boot`; checagem de imutabilidade, started_at com tz                |
| dispatch   | Rotina-fake retornando cada `Action`; mock de `reset_for_new_execution` e `get_cost_snapshot` |
| summary    | Captura via caplog estruturado; checa campos obrigatórios, ausência de PII              |
| cli        | `pytest` invoca `main([...])` com várias combinações; checa exit code                   |
| exit codes | Tabela parametrizada cobrindo cada exceção mapeada                                      |
| docs       | Sem teste automatizado — review humano                                                  |

**Gate:** `pytest`, `ruff check src/`, `mypy src/orchestrator/` limpos. Sem chamadas a OpenAI real (já é mockado em M3).

---

## Riscos e Mitigações

| Risco                                                            | Mitigação                                                                            |
|------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| Auto-discovery quebra import de produção                         | `discover()` captura exceção por módulo e segue; rotina problemática some da lista   |
| `get_cost_snapshot` antes de `reset_for_new_execution`           | Retorna zeros (`CostSnapshot(0,0,0.0)`) — nunca lança                                |
| `boot()` falha cedo demais para logger                           | `summary.emit_boot_failure` escreve JSON em stderr                                   |
| Testes da CLI poluem o `_REGISTRY` global                        | Fixture `_clean_registry` faz `_REGISTRY.clear()` em torno do teste                  |
| Rotina chama `sys.exit` por engano                               | CLI captura `SystemExit` e mapeia para exit code 1 (não 0); summary é emitido       |
| `pkgutil.iter_modules` lê só primeiro nível                      | Documentado em `routines/__init__.py`; limitação aceita                              |

---

## Open Questions (resolver durante implementação)

1. **`BoundLogger` de structlog vs stdlib `LoggerAdapter`** — depende do que `logger.setup.get_logger` retorna hoje. Validar no T01.
2. **`Settings` valida ausência de API key OpenAI mesmo para rotinas que não chamam LLM?** Se sim, dry-run de uma rotina sem LLM ainda exige a key. Decidir: validar lazy em `reset_for_new_execution` (preferido) ou exigir sempre (mais simples).
3. **Nome do pacote raiz de rotinas: `routines` ou `consigaz.routines`?** Atual estrutura usa pacotes flat (`orchestrator`, `desktop`, etc.). Manter `routines` flat por consistência.

Decisões dessas três entram no STATE.md ao serem tomadas.
