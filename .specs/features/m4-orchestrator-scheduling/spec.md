# M4 — Orquestrador e Agendamento

## Problem Statement

M0–M3 entregaram as camadas: fundação (config, logging, secrets), desktop (ancoragem visual cross-platform), web (Playwright com sessão persistida) e inteligência (validação + LLM + roteador). Hoje existe um esqueleto de CLI (`orchestrator/cli.py`) que apenas faz `boot()` e sai — não há **registro de rotinas**, **despacho real**, **integração das camadas** nem **resumo de execução agendável**.

M4 entrega o ponto de entrada de produção:

1. **Registry de rotinas** (decorator `@register("nome")`) — descoberta automática de rotinas em `src/routines/`, evitando despacho por reflexão ad-hoc.
2. **Contexto de rotina** (`RoutineContext`) — DI explícito do que cada rotina precisa: settings, logger, platform, dry-run flag, ciclo da camada de inteligência (`reset_for_new_execution`).
3. **CLI completa** — `--routine`, `--list`, `--dry-run` com semântica definida (boot+validação+LLM, **sem efeito web**), exit codes mapeados por classe de erro.
4. **Sumário estruturado** — uma linha JSON `execution_summary` ao fim de cada execução (routine, duration_s, action, tokens_in/out, cost_usd, exit_code), cron-friendly para grep/alertas.
5. **Documentação de agendamento** — receitas em `docs/scheduling.md` para cron + LaunchAgent (macOS) e Task Scheduler (Windows), explicando como interpretar exit codes e ler o `.json` log.

A primeira rotina real entra em M5; M4 entrega o **chassis** sobre o qual M5 vai plugar a rotina-piloto via `@register`. Sem M4, M5 não tem onde se encaixar.

## Goals

- [ ] `orchestrator/registry.py` com decorator `@register("nome")` + `get(name)` + `list_names()`; descoberta automática varre `src/routines/` no startup
- [ ] `orchestrator/context.py` com `RoutineContext` (frozen dataclass): platform, settings, logger, routine_name, dry_run, started_at
- [ ] `orchestrator/dispatch.py` com `dispatch(name, ctx)` que invoca `reset_for_new_execution(settings)`, chama a rotina, captura métricas, emite summary
- [ ] `orchestrator/summary.py` que coleta tokens/custo do `CostTracker` + duração + action e emite evento `execution_summary` no logger estruturado
- [ ] CLI estendida: `--list`, `--routine`, `--dry-run` com mapeamento claro de exit codes (0/1/2/3/4/5)
- [ ] Contrato `Routine = Callable[[RoutineContext], RoutineResult]` com `RoutineResult(action, evidence, exit_code_hint)`
- [ ] `src/routines/__init__.py` (auto-discovery via `pkgutil.iter_modules`) — rotinas se auto-registram no import
- [ ] `docs/scheduling.md` com receitas: crontab, LaunchAgent (`.plist`), Task Scheduler (`schtasks /create`), incluindo leitura do exit code e do `.json` log
- [ ] 100% das rotas (registry, dispatch, summary, CLI args) cobertas por testes — sem rotinas reais (uma rotina-fixture serve para os testes)
- [ ] Zero quebra de M0–M3: `boot()` segue exportado, sinais de log existentes preservados

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rotinas reais de produção | M5 — depende do domínio Consigaz |
| Helper que gera arquivos cron/.plist/.xml | Decisão da fase de discuss: documentação em markdown é suficiente para v1 |
| Health-check endpoint (`--health-check`) | YAGNI v1; pode entrar quando houver demanda real de monitoramento externo |
| Múltiplas rotinas em paralelo na mesma run | Robô é single-instance por máquina (PROJECT constraint) |
| Retry de rotina inteira em falha | Cron/LaunchAgent já reagenda; complexidade não justificada |
| Daemon residente / loop interno | Fora do escopo — agendamento é responsabilidade do SO |
| Persistência de histórico de execuções (DB) | Já vive nos `.json` logs; dashboard é Deferred Idea |

---

## User Stories

### P1: Registry e Despacho ⭐ MVP

**Como** desenvolvedor de uma rotina de automação,
**eu quero** declarar uma função `run(ctx)` e marcá-la com `@register("nome")`,
**para** que o orquestrador a descubra e despache sem editar a CLI.

**Acceptance Criteria:**
- [ ] **ORC-1.1** — `@register("foo")` aplicado a `def run(ctx: RoutineContext) -> RoutineResult` torna `"foo"` despachável via `python -m orchestrator --routine foo`
- [ ] **ORC-1.2** — Nome duplicado em `@register` lança `RoutineRegistryError("nome 'foo' já registrado")` no import
- [ ] **ORC-1.3** — `registry.list_names()` retorna lista ordenada alfabeticamente
- [ ] **ORC-1.4** — `registry.get("inexistente")` lança `UnknownRoutineError("rotina 'inexistente' não registrada — disponíveis: [...]")` listando as válidas
- [ ] **ORC-1.5** — Descoberta automática: importar `routines` carrega todos os submódulos via `pkgutil.iter_modules`, disparando os `@register`
- [ ] **ORC-1.6** — Falha em import de uma rotina não derruba o orquestrador inteiro: log de erro estruturado + rotina é omitida da listagem
- [ ] **ORC-1.7** — Nomes inválidos (`/`, `\`, `..`, vazio, espaço) rejeitados por `@register` com `RoutineNameError`

### P1: Contrato de Rotina e Contexto ⭐ MVP

**Como** autor de uma rotina,
**eu quero** receber tudo que preciso via um `RoutineContext` imutável,
**para** que minha função seja testável e independente do resto do orquestrador.

**Acceptance Criteria:**
- [ ] **ORC-2.1** — `RoutineContext` é `@dataclass(frozen=True)` com campos: `platform: Platform`, `settings: Settings`, `logger: BoundLogger`, `routine_name: str`, `dry_run: bool`, `started_at: datetime`
- [ ] **ORC-2.2** — `RoutineResult(action: Action, evidence: dict, exit_code_hint: int | None = None)` — `Action` reusa o enum de M3 (`intelligence.types.Action`)
- [ ] **ORC-2.3** — Tipagem do contrato: `Routine = Callable[[RoutineContext], RoutineResult]` exportado de `orchestrator/types.py`
- [ ] **ORC-2.4** — `RoutineContext.started_at` é UTC com timezone (`datetime.now(UTC)`), não naive
- [ ] **ORC-2.5** — `logger` no contexto já vem bound com `routine=<nome>` para todo evento herdar essa chave

### P1: CLI e Exit Codes ⭐ MVP

**Como** operador rodando o robô via cron/Task Scheduler,
**eu quero** exit codes determinísticos por classe de erro,
**para** que o agendador consiga distinguir falha de config, falha de rotina e sucesso.

**Acceptance Criteria:**
- [ ] **ORC-3.1** — `python -m orchestrator --list` imprime rotinas registradas (uma por linha) e sai com 0
- [ ] **ORC-3.2** — `python -m orchestrator --routine foo` invoca `dispatch("foo", ctx)` e retorna exit code conforme tabela
- [ ] **ORC-3.3** — `python -m orchestrator` (sem args) imprime help e sai com 0
- [ ] **ORC-3.4** — `--routine` e `--list` são mutuamente exclusivos (argparse → exit 2)
- [ ] **ORC-3.5** — Tabela de exit codes implementada:
  - `0` — sucesso (`Action.PROCEED_TO_WEB` ou rotina concluída sem exceção)
  - `1` — falha genérica não classificada
  - `2` — erro de configuração (`ValidationError` do pydantic, falta de env var)
  - `3` — plataforma não suportada (`UnsupportedPlatformError`)
  - `4` — rotina desconhecida (`UnknownRoutineError`)
  - `5` — rotina decidiu abortar (`Action.ABORT_IN_DESKTOP` ou `RAISE_EXCEPTION`) — agendador trata como "rodou mas não fez o que devia"
- [ ] **ORC-3.6** — `--dry-run` propaga `ctx.dry_run=True`; semântica documentada: rotina deve executar desktop+validação+LLM mas pular submit web (contrato — fiscalização cabe à rotina, não ao orquestrador)
- [ ] **ORC-3.7** — `argparse` produz help em PT-BR (mesma língua dos demais módulos)

### P1: Sumário de Execução ⭐ MVP

**Como** operador inspecionando execuções agendadas,
**eu quero** uma linha JSON `execution_summary` no fim de cada run,
**para** que eu possa `grep execution_summary` no `.json` e ver tudo em uma linha.

**Acceptance Criteria:**
- [ ] **ORC-4.1** — `dispatch()` emite `log.info("execution_summary", ...)` em **todo** caminho de saída (sucesso, erro de rotina, exceção)
- [ ] **ORC-4.2** — Campos obrigatórios do summary: `routine`, `duration_s` (float, 3 casas), `action` (string do enum ou `"error"`), `tokens_in`, `tokens_out`, `cost_usd` (4 casas), `exit_code`, `dry_run`
- [ ] **ORC-4.3** — Tokens e custo vêm de `intelligence.llm.get_cost_tracker()` (ou função equivalente exposta em M3); se rotina não chamou LLM, valores são `0`
- [ ] **ORC-4.4** — `started_at` (ISO 8601 UTC) e `finished_at` também presentes no summary
- [ ] **ORC-4.5** — Em exceção não tratada da rotina: action=`"error"`, `error_type` e `error_msg` adicionados; exit_code reflete a classe da exceção
- [ ] **ORC-4.6** — Summary nunca contém prompt/resposta crua, PII ou segredos — só campos de telemetria

### P1: Integração com M3 ⭐ MVP

**Como** rotina,
**eu quero** que o orquestrador inicialize a camada de inteligência por execução,
**para** que tokens e custo de chamadas anteriores não vazem entre rotinas.

**Acceptance Criteria:**
- [ ] **ORC-5.1** — `dispatch()` chama `intelligence.reset_for_new_execution(settings)` ANTES de invocar a rotina (decisão STATE M3)
- [ ] **ORC-5.2** — Se reset lançar (settings inválidas para LLM), exit code é 2 (config error)
- [ ] **ORC-5.3** — `RoutineContext` NÃO inclui cliente OpenAI — rotinas importam `from intelligence.llm import call_llm` diretamente (mantém M3 como dependência explícita)

### P2: Documentação de Agendamento

**Como** operador instalando o robô numa máquina nova,
**eu quero** receitas copiáveis de cron/LaunchAgent/Task Scheduler,
**para** que eu agende sem reinventar comando.

**Acceptance Criteria:**
- [ ] **ORC-6.1** — `docs/scheduling.md` contém seção macOS com receita `crontab` E receita `LaunchAgent` (.plist completo, com `WorkingDirectory`, `StandardOutPath`, `StandardErrorPath`)
- [ ] **ORC-6.2** — `docs/scheduling.md` contém seção Windows com receita `schtasks /create` E equivalente XML para import via Task Scheduler GUI
- [ ] **ORC-6.3** — Tabela de exit codes replicada em `docs/scheduling.md` com sugestão de tratamento por exit code
- [ ] **ORC-6.4** — Snippet de como tail-ar `.json` log e filtrar `execution_summary` com `jq`
- [ ] **ORC-6.5** — README principal linka para `docs/scheduling.md` na seção de operação

### P3: Robustez Operacional

**Como** operador,
**eu quero** que falhas de boot não percam o sumário,
**para** que eu sempre tenha um registro estruturado da tentativa.

**Acceptance Criteria:**
- [ ] **ORC-7.1** — Exceção em `boot()` ANTES de logger inicializar → fallback escreve summary mínimo em stderr como JSON puro (`{"event":"execution_summary","action":"boot_error",...}`)
- [ ] **ORC-7.2** — SIGINT (Ctrl-C) durante rotina → exit code 130 (convenção POSIX), summary emitido com `action="interrupted"`
- [ ] **ORC-7.3** — `dispatch()` é idempotente em termos de logging: chamadas em sequência produzem summaries independentes

---

## Non-Functional Requirements

- **Cross-platform:** módulo `orchestrator/` não importa nada SO-específico; toda diferença passa por `platform_info` ou pelos adapters de M1
- **Tempo de startup:** `--list` e `--help` em <300ms em máquina típica (auto-discovery não pode ler templates nem inicializar Playwright)
- **Isolamento de testes:** discovery de rotinas em testes usa pacote alternativo (`tests/fixtures/routines/`) injetado por monkeypatch, não polui produção
- **Compatibilidade:** `boot()` e `BootContext` existentes continuam exportados com a mesma assinatura — M3 e tests atuais não quebram

---

## Dependencies & Assumptions

- M3 expõe `intelligence.reset_for_new_execution(settings)` e algum getter público de `CostTracker` (validar — se não houver, criar como subtask de M4)
- `intelligence.types.Action` é o enum único de ações; M4 não duplica
- `logger.setup.get_logger` retorna `BoundLogger` (structlog-like) — confirmar API real
- `pkgutil.iter_modules` é suficiente para auto-discovery (não há rotinas em subpacotes aninhados — se houver, expandir)

---

## Glossary

- **Routine** — função `(RoutineContext) -> RoutineResult` registrada com `@register("nome")`
- **Dispatch** — invocação de uma rotina nomeada com tudo já inicializado (boot, intelligence reset, logger bound)
- **Execution summary** — evento de log estruturado emitido uma vez por run com métricas agregadas
- **Exit code hint** — sugestão que a rotina retorna no `RoutineResult` para sobrescrever o default da `Action`
