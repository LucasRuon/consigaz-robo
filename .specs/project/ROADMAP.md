# Roadmap

**Current Milestone:** M6 — Rotina TOTVS de Produção
**Status:** M0–M5 concluídos ✅ (macOS) — pronto para M6 (depende de mapeamento TOTVS)

---

## M0 — Fundação Cross-Platform

**Goal:** Esqueleto do projeto funcional em macOS e Windows: dependências instalam, estrutura modular respeitada, logging operacional, CI valida importação dos módulos nos dois SOs.

**Target:** Antes de qualquer rotina real ser implementada.

### Features

**Setup do projeto** — DONE ✅

- Estrutura de diretórios conforme PRD (`orchestrator/`, `desktop/`, `web/`, `intelligence/`, `config/`, `assets/templates/`, `logs/errors/`, `tests/`)
- `pyproject.toml` + `uv.lock` com pinning estrito; smoke test que importa `cv2`, `playwright`, `pyautogui` em ambos SOs
- `Makefile` ou `tasks.py` com comandos cross-platform (setup, run, test, lint)
- README de instalação documentando passos por SO (incluindo permissões de Acessibilidade no macOS e UAC no Windows)

**Camada de configuração e segredos** — DONE ✅

- `config.py` baseado em `pydantic-settings` carregando `.env`
- Wrapper `secrets.py` usando `keyring` (Keychain no mac, Credential Manager no Windows) com fallback `.env`
- Validação: nenhum segredo aparece em log nem em screenshot

**Logging estruturado** — DONE ✅

- Logger com saída dupla: `.log` humano + `.json` estruturado
- Captura automática de screenshot em exceção, salvo em `logs/errors/<timestamp>_<rotina>.png`
- Sanitização: regex de campos sensíveis antes de gravar

---

## M1 — Camada Desktop com Abstração de Plataforma

**Goal:** Módulo Desktop capaz de abrir o app alvo, esperar carregamento por ancoragem visual e interagir com campos — funcionando idêntico em macOS e Windows.

### Features

**Abstração de plataforma (`desktop/platform/`)** — DONE ✅

- Interface `PlatformAdapter` com métodos: `launch_app`, `focus_window`, `modifier_key`, `clipboard_copy/paste`
- Implementação `mac.py` (AppleScript via `subprocess`, tecla `cmd`)
- Implementação `win.py` (`pygetwindow` + `pywin32`, tecla `ctrl`)
- Factory baseada em `sys.platform`
- Testes unitários com mock para cada adapter

**Ancoragem visual (OpenCV)** — DONE ✅

- Função `wait_for_template(path, timeout=15s, threshold=0.8)` com polling
- Tratamento: timeout → screenshot + exceção customizada
- Fallback `assets/templates/{darwin,win32}/` → `assets/templates/` (GA-01)

**Interações primitivas** — DONE ✅

- `click_at_template(path)`, `type_text(text)`, `clear_field()`, `extract_via_clipboard()`
- Zero coordenadas hardcoded — toda posição vem de template matching
- Wrapper try/except obrigatório (NFR-5.2)

---

## M2 — Camada Web (Playwright)

**Goal:** Módulo Web capaz de abrir navegador com sessão persistida, navegar formulários multi-etapa e injetar dados via seletores DOM robustos.

### Features

**Sessão persistente** — DONE ✅

- Diretório de profile persistente cross-platform (`~/.consigaz-robo/playwright-profile/`)
- Fluxo de primeiro login manual documentado; depois reusa cookies
- Cabeçalhos humanos estáveis (mitigação CAPTCHA)

**Navegação e preenchimento** — DONE ✅

- Seletores em `config/selectors.json` (zero seletor hardcoded em código)
- Helper `fill_form(data, mapping)` que mapeia chaves → seletores
- Tratamento nativo de modais/pop-ups e carregamento assíncrono
- Captura de ID de transação ao sucesso

---

## M3 — Camada de Inteligência

**Goal:** Validação determinística + análise de texto livre via OpenAI, com decisão condicional (aprovado → web, reprovado → exceção).

**Plan:** `.specs/features/m3-intelligence-layer/` (spec.md + design.md + tasks.md — 30 requisitos INT-*, 10 tasks)

### Features

**Validação estruturada (Pydantic + helpers Pandas)** — DONE ✅

- Schema declarativo (campos obrigatórios, formatos, ranges)
- Retorno: `ValidationResult` com `is_valid`, `errors`, `warnings`
- Validação roda ANTES de chamar LLM (economia de tokens)

**Cliente OpenAI** — DONE ✅

- Wrapper com retry exponencial (`tenacity`)
- Prompts versionados em `config/prompts/` (não no código)
- Tipagem forte da resposta (Pydantic)
- Limite de custo por execução (guard rail)

**Roteador de decisão** — DONE ✅

- Função pura `decide(structured_result, llm_result) → Action` (sem side-effects)
- Testes determinísticos cobrindo aprovado/reprovado/exceção

---

## M4 — Orquestrador e Agendamento

**Goal:** Ponto de entrada que carrega config, despacha rotinas, agrega logs e é agendável em cron (macOS) e Task Scheduler (Windows).

**Plan:** `.specs/features/m4-orchestrator-scheduling/` (spec.md + design.md + tasks.md — 23 requisitos ORC-*, 11 tasks de código + 1 de housekeeping)

### Features

**CLI do orquestrador** — DONE ✅

- `python -m orchestrator [--list] [--routine NAME [--dry-run]]`
- Registry de rotinas (`@register`) com auto-discovery em `src/routines/`
- `RoutineContext` frozen (DI) + `RoutineResult(action, evidence, exit_code_hint)`
- Exit codes mapeados (0/1/2/3/4/5/130) por classe de exceção
- `execution_summary` (linha JSON estruturada) por execução — tokens, custo, duração
- Fallback `emit_boot_failure` em stderr quando o logger ainda não existe

**Documentação de agendamento** — DONE ✅

- `docs/scheduling.md` — crontab + LaunchAgent (.plist) no macOS
- `schtasks` + XML para Task Scheduler no Windows
- Tabela de exit codes com tratamento sugerido por código
- Snippets `jq` para filtrar/sumarizar o evento `execution_summary` nos `.json`
- README principal aponta para `docs/scheduling.md`

---

## M5 — Primeira Rotina End-to-End

**Status:** M0-M5 concluídos ✅ (macOS) — pronto para M6

**Goal:** Provar que o chassis cabeado em M0-M4 funciona em execução real, usando alvos neutros (Calculadora + httpbin) para deixar a rotina TOTVS para M6 quando o domínio for mapeado.

**Plan:** `.specs/features/m5-pilot-smoke/` (spec.md + design.md + tasks.md — 9 tasks, AC-1 a AC-7)

### Features

**Rotina-piloto** — DONE ✅

Implementada como rotina-esqueleto `pilot-smoke`; rotina TOTVS de produção fica em M6.

- `src/routines/pilot_smoke.py` com `@register("pilot-smoke")` e pipeline canônico de 21 passos
- Schemas `PilotSmokeData` + `PilotSmokeLLM` em `intelligence/schemas/pilot_smoke.py`
- Prompt `config/prompts/pilot-smoke.md` versionado (v1) com `response_schema`
- Bloco `pilot_smoke` em `config/selectors.json` (formulário httpbin)
- Templates Calculadora em `assets/templates/pilot-smoke/darwin/` (placeholders — substituir antes do E2E real)
- 6 testes unitários (mocks) + 3 testes E2E gateados por `RUN_E2E_PILOT_SMOKE=1`
- Checklist Windows em `CHECKS.md` (pendente máquina)

---

## M6 — Rotina TOTVS de Produção

**Goal:** Implementar a primeira rotina real de domínio Consigaz, automatizando um processo manual concreto entre TOTVS (desktop) e a plataforma web Consigaz, reusando exatamente o padrão E2E provado em M5.

**Bloqueador:** Mapeamento TOTVS pendente — versão do produto, telas alvo, campos a extrair, processo manual passo-a-passo, e mapeamento da plataforma web Consigaz (URL base, login, formulários).

### Features (placeholder — refinar após mapeamento)

**Rotina TOTVS** — TODO

- Spec do processo TOTVS escolhido (sessão de discuss com operador)
- Schemas `<rotina>Data` + `<rotina>LLM` herdando contrato canônico de M5
- Prompt LLM com placeholders de domínio
- Templates TOTVS capturados em `assets/templates/<rotina>/`
- Seletores Consigaz mapeados em `config/selectors.json`
- Testes unit + E2E gateado por env var

---

## Future Considerations

- Abstração multi-LLM (Anthropic, modelos locais)
- Empacotamento como executável (`.dmg`, `.exe`) para distribuição
- Dashboard de execuções (web simples lendo os `.json` logs)
- Multi-máquina com fila central (Redis/SQS) — sai do escopo single-host
- Suporte a Linux para servidores headless
- Modo "atendido" com confirmação humana em decisões de baixa confiança da LLM
