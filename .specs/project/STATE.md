# State

Memória persistente entre sessões: decisões, blockers, lições, todos, ideias adiadas.

---

## Decisions

### 2026-05-28 — Suporte cross-platform (macOS + Windows)
O PRD foi escrito para macOS Apple Silicon apenas. Decisão: estender para Windows desde a v1, via camada de abstração `desktop/platform/{mac,win}.py`. A lógica de negócio (orquestrador, web, inteligência) permanece única; apenas foco de janela, atalhos modificadores e launcher de app variam por SO.
**Implicação:** Toda dependência precisa de wheel pré-compilada para `arm64-darwin` E `win-amd64`. Bibliotecas que compilam do source são vetadas.

### 2026-05-28 — LLM = OpenAI (GPT-4/5)
Provedor único na v1. Sem abstração multi-LLM por ora (YAGNI). Prompts ficam versionados em `config/prompts/` para troca futura sem refatoração de código.

### 2026-05-28 — Execução: agendada em uma máquina dedicada
Single-host. Sem coordenação multi-instância na v1. Agendamento documentado via cron (macOS) e Task Scheduler (Windows), não embutido no código.

### 2026-05-28 — Gerenciador de ambiente: `uv`
Mais rápido que `pip`, lockfile reproduzível, funciona idêntico em macOS e Windows. `venv + pip` fica como fallback documentado se houver resistência.

### 2026-05-28 — Organização de templates de imagem: fallback por SO (GA-01)
Templates ficam em `assets/templates/` (fallback) com subpastas opcionais `darwin/` e `win32/` para overrides SO-específicos. `wait_for_template()` busca primeiro em `assets/templates/{sys.platform}/`, depois cai em `assets/templates/`. Isso permite começar com pasta única e adicionar overrides apenas quando a UI divergir entre SOs.
**Implicação:** Ao capturar novos templates, o operador salva em `assets/templates/` por padrão; só move para subpasta de SO se o match falhar na outra plataforma.

### 2026-05-28 — M2: Convenção de seletores web (`selectors.json`)
Organização por página (`dict[str, dict[str, str]]`): chave de topo = nome da página, sub-chave = nome do elemento. `fill_form(page, data)` recebe nome da página para lookup. Chaves prefixadas com `_` são metadados (ex: `_session_sentinel`) e são ignoradas pelo `fill_form`. Nomes de elementos em snake_case semântico.
**Implicação:** Ao mapear novas telas da plataforma Consigaz (M5), o operador adiciona um bloco por página em `config/selectors.json`. Nenhum seletor vai para o código Python.

### 2026-05-28 — M2: Browser headed por padrão
`headless=False` como padrão — robô roda em máquina dedicada com display. Configurável via `settings.web_headless` (env var `WEB_HEADLESS=true` para headless quando confirmado que o sistema alvo não detecta).

### 2026-05-28 — M2: Detecção de sessão expirada (URL + sentinel)
Estratégia OR: verifica padrões de URL de login (configurável via `settings.web_login_url_patterns`) e opcionalmente presença de elemento sentinel (`_session_sentinel` em `selectors.json`). Se URL bate padrão OU sentinel não aparece em 3s → `LoginRequiredError`. Permite detecção de redirects silenciosos (sem mudança de URL).

### 2026-05-28 — M3: Schema de validação híbrido (Pydantic + helpers Pandas)
Schemas de validação ficam como subclasses de `pydantic.BaseModel` com `model_config = {"extra": "forbid", "strict": True}`. Helpers Pandas (`validate_range`, `compare_against_history`) vivem em `intelligence/analysis.py` separados do caminho crítico — importados apenas pelas rotinas que precisam de comparação histórica.
**Implicação:** `validation.py` não importa Pandas (cold start mais rápido). Cada rotina (M5) define seu schema em `intelligence/schemas/<rotina>.py` decorado com `@register("nome")`. `analysis.py` é opt-in.

### 2026-05-28 — M3: `Decision` com confidence (antecipa modo atendido)
Roteador retorna `Decision(action: Action, reason: str, evidence: dict, confidence: float)`. Campo `confidence` é incluído já na v1 mesmo que o modo "atendido" (humano confirma baixa confiança) seja Deferred Idea — é barato adicionar agora e custoso refatorar depois. v1 trata `confidence < settings.llm_min_confidence` (default 0.7) como `Action.RAISE_EXCEPTION`. Mapeamento da resposta da LLM: `approve→PROCEED_TO_WEB`, `reject→ABORT_IN_DESKTOP`, `escalate→RAISE_EXCEPTION`.
**Implicação:** Toda resposta tipada da LLM (`response_model`) deve expor `decision: Literal["approve","reject","escalate"]` e `confidence: float`. Schemas de rotina em M5 herdam dessa convenção. `decide()` lança `RouterContractError` se o contrato não for satisfeito.

### 2026-05-28 — M3: Guard rail de custo = tokens (hard) + USD (warning)
Limite de execução em tokens é o cap executável (`settings.llm_token_hard_cap`, default 100k) — estoura `TokenBudgetExceededError` ANTES da chamada. USD é só warning no log estruturado (`settings.llm_cost_warning_usd`, default 1.0) — não bloqueia. Tabela de preços vive em `settings.llm_model_prices: dict[model, (price_in_per_1k, price_out_per_1k)]` editável manualmente quando OpenAI muda pricing.
**Implicação:** CostTracker é estado de módulo global em `intelligence/llm.py`; orquestrador (M4) deve chamar `intelligence.reset_for_new_execution(settings)` no início de cada rotina. Mudança de preço da OpenAI exige update em `config.py` — comportamento de execução não muda.

### 2026-05-28 — M3: Prompts em `.md` com frontmatter YAML
Prompts ficam em `config/prompts/<nome>.md`. Frontmatter delimitado por `---` com `version` (obrigatória), `model` (opcional, default `settings.llm_default_model`), `temperature` (opcional, default `settings.llm_default_temperature`), `response_schema` (opcional, nome de classe no registry). Corpo é template com placeholders `{var}`. Render via `str.format_map` — placeholder ausente lança `PromptRenderError(missing=[...])`. Nomes com `/`, `\` ou `..` rejeitados (`PromptNameError`).
**Implicação:** Mantenedores editam prompts sem tocar em Python; diffs ficam legíveis em PR. Versão obrigatória força bump consciente. `response_schema` referencia classe via registry em `intelligence/schemas/__init__.py` — falha cedo no `load()` se schema não registrado.

### 2026-05-28 — Validação cross-platform de M0 executada em macOS
Checklist `CHECKS.md` executado em macOS arm64 (Darwin), Python 3.14.4.
Todos os itens executáveis da seção macOS validados (9 de 10 como `[x]`, 1 como
`[~]` por exigir permissão Gravação de Tela — coberto por teste automatizado
com FakeScreenshot). `uv sync`, `inv test` (72/72), `inv lint`, `inv typecheck`,
`python -m orchestrator --help` e `inv smoke` retornam exit 0. Logs `.log` +
`.json` gerados com timestamp + routine no nome; sanitizador mascara
`password=***`; encoding UTF-8 sem mojibake.
Seção Windows fica **pendente** — usuário não tem máquina Windows acessível
no momento. M0 só pode ser fechado como "done cross-platform" após validação
em Windows.
**How to apply:** quando o ambiente Windows for disponibilizado, rodar o
mesmo checklist e atualizar a seção Windows do `CHECKS.md`.

### 2026-05-28 — M4: boundary com M3 via `get_cost_snapshot()` público
A camada `intelligence` ganhou `CostSnapshot` (frozen) + `get_cost_snapshot()`
público. M4 lê o snapshot no `summary.emit` sem tocar no `_cost_tracker`
interno. Quando nenhum reset foi chamado ainda (caminho de erro precoce),
retorna zeros — **nunca lança** — para que o sumário sempre saia.
`CostTracker` ganhou `tokens_in` e `tokens_out` separados (além do
`tokens_used` agregado) para satisfazer ORC-4.2 sem inferência no orquestrador.
**How to apply:** rotinas (M5+) que precisarem de telemetria de custo durante a
execução podem chamar `from intelligence import get_cost_snapshot` em vez de
importar internals.

### 2026-05-28 — M4: semântica de `--dry-run` é contrato, não fiscalização
`--dry-run` propaga `ctx.dry_run=True`. **A rotina é responsável por respeitar
o flag** (executar desktop+validação+LLM mas pular o submit web). O
orquestrador não inspeciona ações de rede nem bloqueia chamadas web — isso
acoplaria M4 a internals dos módulos `desktop`/`web`. Cada rotina (M5+) testa
o seu próprio caminho dry-run.
**How to apply:** ao escrever rotinas em M5, fazer `if ctx.dry_run: return
RoutineResult(action=Action.PROCEED_TO_WEB, evidence={"dry_run": True})`
ANTES do `web.submit_form(...)`.

### 2026-05-28 — M4: formato do summary = linha JSON única no logger M0
Uma única entrada `execution_summary` por run, emitida via
`ctx.logger.info("execution_summary", ...)` — nada de arquivo separado, nada
de tabela formatada. Campos obrigatórios: `routine`, `action`, `duration_s`
(3 casas), `tokens_in`, `tokens_out`, `cost_usd` (4 casas), `exit_code`,
`dry_run`, `started_at`, `finished_at`, `evidence_keys`. Em exceção:
`error_type` + `error_msg` adicionados; `action="error"`. Em falha de boot
(antes do logger inicializar): fallback escreve JSON puro em stderr via
`emit_boot_failure`. **Summary NUNCA contém valores de `evidence`** — apenas
as chaves ordenadas, para evitar PII e segredos no log.
**How to apply:** operadores fazem `grep '"event":"execution_summary"'
logs/*.json | jq` — receitas em `docs/scheduling.md`. Dashboards futuros
consomem o mesmo evento.

### 2026-05-28 — M4: `__init__.py` preserva submódulos no namespace
`orchestrator.__init__` faz `from orchestrator import boot, dispatch` para
preservar `orchestrator.boot` e `orchestrator.dispatch` como módulos (não
funções). As funções ficam acessíveis como `orchestrator.boot.boot` e
`orchestrator.dispatch.dispatch`. Razão: testes legacy (M0–M3) usam
`monkeypatch.setattr("orchestrator.boot.current_platform", ...)` e `pytest`
resolve via getattr-chain — se o nome `boot` fosse a função, o monkeypatch
quebrava. Trade-off aceito: `from orchestrator import boot` retorna o módulo;
quem quiser a função usa `from orchestrator.boot import boot`.
**How to apply:** ao adicionar submódulos no orchestrator que também
exportam função homônima (`registry`, etc), seguir o mesmo padrão.

### 2026-05-28 — M4 concluído: chassis de produção do orquestrador
Implementadas as 11 tasks de código do `.specs/features/m4-orchestrator-scheduling/`
(T01–T11). 23 requisitos ORC-* cobertos. Gate completo passa: `pytest` (377
testes totais, 56 novos), `ruff check src/` e `mypy src/orchestrator/`
limpos. Entregue: registry com decorator + auto-discovery de `src/routines/`,
`RoutineContext` frozen com logger bound, `dispatch` com mapping de Action
para exit codes, CLI estendida (`--list`, exit codes 0/1/2/3/4/5/130),
`emit_boot_failure` em stderr e `docs/scheduling.md` com receitas cron +
LaunchAgent + schtasks.
**How to apply:** M5 pode criar a primeira rotina real em
`src/routines/<nome>.py` com `@register("nome")` e função
`def run(ctx: RoutineContext) -> RoutineResult`. Auto-discovery a carrega
sem editar a CLI.

### 2026-05-29 — M5 concluído: chassis E2E provado via pilot-smoke
Implementadas as 9 tasks de `.specs/features/m5-pilot-smoke/` (T01–T09). A
rotina `pilot-smoke` exercita as 4 camadas (desktop Calculadora → validação
Pydantic → LLM OpenAI → web httpbin) ponta a ponta em macOS. Gate completo
passa: `pytest` (394 testes totais, 17 novos; 3 E2E skipped por gating de env
var), `ruff` e `mypy` limpos nos arquivos novos. Templates Calculadora
capturados em `assets/templates/pilot-smoke/darwin/` (PLACEHOLDERS 1×1 cinza
no commit inicial — substituir por capturas reais antes do E2E). Windows fica
como checklist manual em `CHECKS.md` (sem máquina disponível).
**Why:** prova que os contratos M0-M4 funcionam em execução real, antes de
investir em domínio TOTVS.
**How to apply:** M6 (TOTVS) reusa exatamente este padrão — `<rotina>Data` +
`<rotina>LLM` schemas, prompt `.md` em `config/prompts/`, bloco em
`selectors.json`, templates em `assets/templates/<rotina>/`, e arquivo único
`src/routines/<rotina>.py` (ou package se crescer).

### 2026-05-29 — M5: contrato canônico de `evidence`
Chaves padrão herdadas por M6+: `operation`, `result`, `llm_decision`,
`llm_confidence`, `llm_summary`, `web_final_url`, `web_status`, `dry_run`.
Em `--dry-run`, `web_*` ficam ausentes. Summary M4 expõe apenas
`evidence_keys` ordenadas — nunca valores.
**Why:** operadores fazem `grep '"event":"execution_summary"' logs/*.json |
jq` e obtêm o mesmo shape em todas as rotinas. Mudar o shape exige decisão
arquitetural (não pode ser feito ad-hoc por rotina).
**How to apply:** ao escrever a rotina TOTVS, mapear chaves de domínio
(`cliente_id`, `pedido_numero`, etc.) substituindo `operation`/`result`, mas
manter o prefixo `llm_*`/`web_*` para análise transversal.

### 2026-05-28 — M3 concluído: camada de inteligência funcional
Implementadas as 10 tasks do `.specs/features/m3-intelligence-layer/`:
`intelligence/{exceptions,types,validation,analysis,prompts,llm,router,schemas}`.
30/30 requisitos INT-* cobertos. Gate completo passa: `pytest` (321 testes
totais, 109 novos de intelligence), `ruff check src/` e `mypy src/intelligence/`
limpos. Cliente OpenAI mockado (sem chamadas reais em CI). Tabela de preços
em `settings.llm_model_prices`; hard cap de tokens, warning USD, sanitização
de logs (nunca prompt/resposta crua) validados por teste. Router puro com
matriz table-driven.
**How to apply:** M4 (orquestrador) já pode consumir
`intelligence.reset_for_new_execution(settings)` no início da rotina,
`validate → call_llm → decide` em sequência e despachar pela `Action`.
Prompts reais e schemas concretos chegam em M5 com o domínio Consigaz.

---

## Blockers

### Bloqueador de M6 — Mapeamento TOTVS pendente
Para escrever a rotina TOTVS de produção precisamos de: (1) versão/edição do
produto TOTVS instalada, (2) telas alvo (capturas + nomes de janelas), (3)
campos exatos a extrair, (4) processo manual completo a automatizar
(passo-a-passo do operador), (5) plataforma web Consigaz onde os dados são
injetados (URL base, fluxo de login, formulários). Sem esse mapeamento, M6
fica em backlog. Os bloqueadores de M5 (app desktop, plataforma web,
rotina-piloto) foram **desbloqueados** ao escolher Calculadora + httpbin como
alvos neutros — M6 retoma o problema real.

### Pendente para fechar M0 — Validação no Windows
Sem máquina Windows hoje. `CHECKS.md` tem seção Windows aguardando execução.
M0 está funcionalmente completo (16/16 tasks) mas só vira "verified
cross-platform" após esse checklist passar em Windows 10/11 x86_64.

---

## TODOs

- Confirmar com o usuário: `uv` ou `venv + pip`?

---

## Deferred Ideas

- Abstração multi-LLM (Anthropic, modelos locais) — fora do escopo v1; reavaliar após M5.
- Empacotamento como executável (.dmg/.exe) — usuário roda via Python por ora.
- Dashboard web lendo os `.json` logs — boa ideia para milestone futura.
- Modo "atendido" com confirmação humana em decisões de baixa confiança da LLM.

---

## Lessons

### 2026-05-28 — Lazy import em adapters de plataforma
`win.py` faz `import pygetwindow` dentro do método `focus_window()`, não no topo do arquivo. Isso permite que o módulo seja importado em macOS (onde pygetwindow não está instalado) sem lançar ImportError. Padrão aplicado a todas as dependências exclusivas de um SO.

### 2026-05-28 — Mocks de factory com lazy import
Testes da factory `get_platform_adapter()` usam `patch.dict("sys.modules", {...})` para injetar módulos falsos. `patch("desktop.platform.mac.MacAdapter")` falha se o arquivo não existe ainda — o approach via `sys.modules` é mais robusto e independente da ordem de implementação.

### 2026-05-28 — pyperclip.paste() retorna Any
`pyperclip` não tem stubs de tipo. `paste()` retorna `Any` — é necessário envolver com `str()` para satisfazer o mypy em modo strict. Adicionado `pyperclip.*` em `ignore_missing_imports` do mypy.

### 2026-05-29 — Fixtures que limpam registries criam acoplamento entre testes
`tests/intelligence/conftest.py::clear_schema_registry` e
`tests/test_orchestrator/conftest.py::clean_registry` zeram os registries
globais (schemas / rotinas). Quando testes rodam na suite inteira, isso
quebra testes posteriores que dependem da chamada `@register` que rodou no
import inicial — Python só importa o módulo uma vez, então o decorator não
dispara de novo. Solução adotada em M5: `conftest.py` autouse em
`tests/test_intelligence/` e `tests/test_routines/` re-registra schemas e
rotina pilot-smoke (idempotente para schemas; write direto no `_REGISTRY`
para rotina porque o decorator do orchestrator rejeita re-registro).
**How to apply:** ao adicionar nova rotina M6+, criar autouse fixture
análogo no conftest do diretório de teste correspondente.

---

## Preferences

- Idioma: Português (PT-BR) para toda comunicação e documentação interna.
- Estilo de commits: a definir na fase de setup (sugestão: Conventional Commits).
