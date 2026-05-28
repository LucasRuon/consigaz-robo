# Roadmap

**Current Milestone:** M2 — Camada Web (Playwright)
**Status:** M1 concluído ✅ — pronto para M2

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

**Sessão persistente** — IN PROGRESS 🚧

- Diretório de profile persistente cross-platform (`~/.consigaz-robo/playwright-profile/`)
- Fluxo de primeiro login manual documentado; depois reusa cookies
- Cabeçalhos humanos estáveis (mitigação CAPTCHA)

**Navegação e preenchimento** — IN PROGRESS 🚧

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

### Features

**CLI do orquestrador** — PLANNED

- `python -m orchestrator [--routine NAME] [--dry-run]`
- Carrega config, valida ambiente, executa rotina, agrega log final
- Exit codes claros para o agendador interpretar

**Documentação de agendamento** — PLANNED

- Receita cron + LaunchAgent (macOS)
- Receita Task Scheduler (Windows)
- Recomendação de logging de runs agendados

---

## M5 — Primeira Rotina End-to-End

**Goal:** Uma rotina real (a ser definida em sessão de spec) executando o happy path completo: desktop → extração → validação → LLM → web → sucesso.

**Bloqueador:** Precisa do app desktop alvo identificado, URL/fluxo da plataforma web Consigaz definidos, e rotina específica escolhida.

### Features

**Rotina-piloto** — PLANNED (escopo a definir)

- Spec da rotina (gray areas serão discutidas)
- Templates de imagem capturados
- Seletores web mapeados
- Prompt da LLM versionado
- Teste end-to-end em ambos SOs

---

## Future Considerations

- Abstração multi-LLM (Anthropic, modelos locais)
- Empacotamento como executável (`.dmg`, `.exe`) para distribuição
- Dashboard de execuções (web simples lendo os `.json` logs)
- Multi-máquina com fila central (Redis/SQS) — sai do escopo single-host
- Suporte a Linux para servidores headless
- Modo "atendido" com confirmação humana em decisões de baixa confiança da LLM
