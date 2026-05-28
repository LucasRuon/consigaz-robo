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

---

## Blockers

### Bloqueador de M5 — Identificação do app desktop alvo
Precisamos do nome/bundle ID do app no macOS (`open -a "Nome do App"`) e do caminho do executável no Windows. Sem isso, não dá pra implementar a primeira rotina end-to-end.

### Bloqueador de M5 — Plataforma web interna da Consigaz
Precisamos da URL base, fluxo de login (form/SSO), e mapa dos formulários alvo. Sem isso, módulo Web fica genérico demais.

### Bloqueador de M5 — Definição da rotina-piloto
Qual processo manual exato será automatizado primeiro? Sem isso, não dá pra escrever spec, capturar templates ou mapear seletores.

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

---

## Preferences

- Idioma: Português (PT-BR) para toda comunicação e documentação interna.
- Estilo de commits: a definir na fase de setup (sugestão: Conventional Commits).
