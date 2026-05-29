# M4 — Tasks

Ordem topológica das tarefas com dependências, reuso e gates. `[P]` = paralelizável após dependências satisfeitas.

Gate global (rodar antes de fechar cada task): `pytest`, `ruff check src/ tests/`, `mypy src/orchestrator/`.

---

## T01 — Expor `CostSnapshot` e `get_cost_snapshot()` em `intelligence`

**What:** Adicionar tipo `CostSnapshot` (frozen dataclass com `tokens_in`, `tokens_out`, `cost_usd`) e função `get_cost_snapshot() -> CostSnapshot` em `intelligence/llm.py`. Lê do `_cost_tracker` atual; retorna zeros se nenhum tracker estiver ativo (não lança).
**Where:** `src/intelligence/llm.py`, `src/intelligence/types.py` (ou novo `costs.py`), `src/intelligence/__init__.py`
**Depends on:** —
**Reuses:** `_cost_tracker` interno já existente em `llm.py`; padrão `@dataclass(frozen=True)` já usado em `types.py`
**Done when:**
- [ ] `from intelligence import get_cost_snapshot, CostSnapshot` funciona
- [ ] Sem reset prévio: retorna `CostSnapshot(0, 0, 0.0)` (NÃO lança)
- [ ] Após reset + call_llm mockado: snapshot reflete uso
**Tests:** `tests/test_intelligence/test_cost_snapshot.py` — 3 casos: sem reset, após reset zerado, após uso
**Gate:** Gate global, sem regressão nos 321 testes existentes

## T02 — `orchestrator/exceptions.py`

**What:** Definir `RoutineRegistryError`, `RoutineNameError`, `UnknownRoutineError` herdando de `Exception` (não de IntelligenceError — domínios separados).
**Where:** `src/orchestrator/exceptions.py`
**Depends on:** —
**Reuses:** padrão de exceções de `intelligence/exceptions.py`
**Done when:**
- [ ] Três classes definidas, `__all__` populado
- [ ] `UnknownRoutineError` aceita `available: list[str]` opcional e formata mensagem listando-os
**Tests:** `tests/test_orchestrator/test_exceptions.py` — instanciação + format da mensagem
**Gate:** Gate global

## T03 — `orchestrator/types.py` (RoutineResult + Routine) [P após T02]

**What:** `RoutineResult` (frozen) com `action: Action`, `evidence: dict[str, Any]`, `exit_code_hint: int | None = None`. Alias `Routine = Callable[["RoutineContext"], RoutineResult]`.
**Where:** `src/orchestrator/types.py`
**Depends on:** T02 (só pra coexistir no pacote; sem dependência funcional)
**Reuses:** `intelligence.types.Action`
**Done when:**
- [ ] Import circular protegido com `TYPE_CHECKING` para `RoutineContext`
- [ ] `RoutineResult.action` aceita qualquer membro do enum `Action`
**Tests:** `tests/test_orchestrator/test_types.py` — construção, frozen, default de exit_code_hint
**Gate:** Gate global

## T04 — `orchestrator/context.py` (RoutineContext) [P após T03]

**What:** `RoutineContext` frozen dataclass conforme ORC-2.1. `from_boot(boot_ctx, *, dry_run, routine_name)` classmethod que faz bind do logger com `routine=<nome>`. `started_at` em UTC tz-aware.
**Where:** `src/orchestrator/context.py`
**Depends on:** T03
**Reuses:** `BootContext` de `orchestrator/boot.py`; `get_logger` de `logger/setup.py`
**Done when:**
- [ ] Frozen, hashable se possível (settings é frozen?)
- [ ] `started_at.tzinfo is not None`
- [ ] `logger` retornado tem chave `routine` em todo evento
**Tests:** `tests/test_orchestrator/test_context.py` — construção via from_boot, imutabilidade, tz, logger bound
**Gate:** Gate global

## T05 — `orchestrator/registry.py` (decorator + discover)

**What:** `_REGISTRY: dict[str, Routine] = {}`. `@register(name)`, `get(name)`, `list_names()`, `discover(package="routines")`. Validação de nome via regex `^[a-z][a-z0-9_-]*$`. Discover usa `pkgutil.iter_modules` + `importlib.import_module`; captura exceção por módulo e loga structured warning, segue.
**Where:** `src/orchestrator/registry.py`
**Depends on:** T02, T03
**Reuses:** padrão de registry de `intelligence/schemas/__init__.py`
**Done when:**
- [ ] Duplicado → `RoutineRegistryError`
- [ ] Nome inválido → `RoutineNameError`
- [ ] `get("xyz")` quando não existe → `UnknownRoutineError(available=list_names())`
- [ ] `discover` resiste a módulo com erro de import (não derruba)
- [ ] Existe helper `_clear()` interno para fixtures de teste
**Tests:** `tests/test_orchestrator/test_registry.py` — register válido, duplicado, nome inválido, get desconhecido, list ordem alfabética, discover com fixture
**Gate:** Gate global

## T06 — `src/routines/__init__.py` (auto-discovery) [P após T05]

**What:** Pacote raiz para rotinas reais. `__init__.py` faz auto-discovery via `pkgutil.iter_modules`. Por enquanto não há rotinas; M5 cria a primeira.
**Where:** `src/routines/__init__.py`
**Depends on:** T05
**Reuses:** lógica de discover de T05 (ou simplesmente chama `orchestrator.registry.discover("routines")`)
**Done when:**
- [ ] `import routines` não falha em diretório vazio
- [ ] Comentário no topo explica padrão p/ M5
**Tests:** `tests/test_routines/test_package.py` — import do pacote vazio
**Gate:** Gate global

## T07 — `orchestrator/summary.py` (emit + emit_error + emit_boot_failure)

**What:** Três funções públicas conforme design. `emit` lê snapshot de M3, calcula duração, monta dict de campos obrigatórios (ORC-4.2), emite `log.info("execution_summary", ...)`. `emit_error` adiciona `error_type` e `error_msg`. `emit_boot_failure` escreve JSON em `sys.stderr` (não usa o logger).
**Where:** `src/orchestrator/summary.py`
**Depends on:** T01, T04
**Reuses:** `intelligence.get_cost_snapshot`, logger estruturado de M0
**Done when:**
- [ ] Summary nunca contém valores de `evidence`, só chaves
- [ ] `cost_usd` arredondado para 4 casas, `duration_s` para 3
- [ ] `emit_boot_failure` produz JSON parseável em stderr
- [ ] Nenhum campo de PII/segredo no payload
**Tests:** `tests/test_orchestrator/test_summary.py` — captura via caplog, parametrizado p/ cada Action e p/ erro; checagem de campos via set comparison
**Gate:** Gate global

## T08 — `orchestrator/dispatch.py`

**What:** `dispatch(name, boot_ctx, *, dry_run) -> int`. Sequência: `registry.get(name)` → `intelligence.reset_for_new_execution(boot_ctx.settings)` → cria `RoutineContext` → executa rotina → `summary.emit` → retorna exit_code. Em exceção da rotina: `summary.emit_error` → re-raise. Tabela `_exit_for_action`.
**Where:** `src/orchestrator/dispatch.py`
**Depends on:** T04, T05, T07
**Reuses:** `intelligence.reset_for_new_execution`
**Done when:**
- [ ] `Action.PROCEED_TO_WEB` → 0
- [ ] `Action.ABORT_IN_DESKTOP`/`RAISE_EXCEPTION` → 5
- [ ] `exit_code_hint` sobrescreve default
- [ ] Exceção da rotina propaga após summary
- [ ] Reset chamado antes da rotina (verificado por ordem de chamadas)
**Tests:** `tests/test_orchestrator/test_dispatch.py` — rotina-fake fixture; cada Action; rotina lança; reset é chamado antes
**Gate:** Gate global

## T09 — Estender `orchestrator/cli.py`

**What:** Adicionar `--list` (mutex com `--routine`), invocar `registry.discover("routines")` antes de listar/despachar, mapear exceções via `_map_exception`, tratar `KeyboardInterrupt` → 130. Help em PT-BR.
**Where:** `src/orchestrator/cli.py`
**Depends on:** T05, T08
**Reuses:** `boot()` existente, exit codes já definidos (estender)
**Done when:**
- [ ] `--list` imprime rotinas em ordem, exit 0
- [ ] `--routine X` invoca dispatch e retorna seu int
- [ ] `--routine X --list` argparse rejeita (exit 2)
- [ ] `UnknownRoutineError` → 4; `RoutineRegistryError` → 4
- [ ] `ValidationError` (pydantic) → 2; `UnsupportedPlatformError` → 3; `KeyboardInterrupt` → 130; default → 1
- [ ] Falha de `boot()` aciona `summary.emit_boot_failure`
**Tests:** `tests/test_orchestrator/test_cli.py` — estender; parametrizar por exit code esperado; monkeypatch de `boot` para forçar exceções
**Gate:** Gate global

## T10 — Atualizar `orchestrator/__init__.py` exports [P após T09]

**What:** Exportar `boot`, `dispatch`, `RoutineContext`, `RoutineResult`, `Routine`, `register`, `get`, `list_names`, `discover` e as exceções de M4.
**Where:** `src/orchestrator/__init__.py`
**Depends on:** T02–T09
**Done when:** `from orchestrator import register, RoutineContext, RoutineResult` funciona
**Tests:** `tests/test_orchestrator/test_public_api.py` — import smoke + `__all__` matches reality
**Gate:** Gate global

## T11 — `docs/scheduling.md`

**What:** Documentação operacional com receitas cron + LaunchAgent (macOS) e schtasks + XML (Windows), tabela de exit codes, snippet `jq` para `execution_summary`. Linkar do README.
**Where:** `docs/scheduling.md`, `README.md` (link)
**Depends on:** T09 (exit codes precisam estar finalizados)
**Done when:**
- [ ] Seção macOS com crontab + LaunchAgent `.plist` completo (paths, log redirect)
- [ ] Seção Windows com `schtasks /create` + XML equivalente
- [ ] Tabela de exit codes com sugestão de tratamento por código
- [ ] Snippet jq filtrando `execution_summary` no `.json`
- [ ] README aponta para `docs/scheduling.md`
**Tests:** review humano; markdown lint opcional
**Gate:** `ruff` (n/a), revisar links manualmente

## T12 — Atualizar STATE.md e ROADMAP.md [P após T11]

**What:** Registrar em STATE.md as 3 decisões finais (boundary M4↔M3, semântica de `--dry-run`, formato do summary). Em ROADMAP.md marcar M4 como `DONE ✅` quando T01–T11 fecharem; M5 vira `IN PROGRESS`.
**Where:** `.specs/project/STATE.md`, `.specs/project/ROADMAP.md`
**Depends on:** T01–T11 verde
**Done when:** Entradas datadas em STATE; ROADMAP refletindo status
**Tests:** n/a
**Gate:** —

---

## Resumo de dependências

```
T01 ─┐
T02 ─┤
T03 ─┤
T04 ──── T05 ──── T06
T01 + T04 ──── T07
T04 + T05 + T07 ──── T08
T05 + T08 ──── T09
T02..T09 ──── T10
T09 ──── T11 ──── T12
```

Paralelizáveis após T05: T06, T07 (uma vez T01+T04 prontas).

---

## Não-objetivos das tasks (lembretes)

- Não criar nenhuma rotina real (M5).
- Não tocar em `desktop/`, `web/`, `intelligence/` além do mínimo de T01.
- Não introduzir framework de DI; `RoutineContext` é DI suficiente.
- Não embutir helper que gera `.plist`/`.xml` — só docs.
