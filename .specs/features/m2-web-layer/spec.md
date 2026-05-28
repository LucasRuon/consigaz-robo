# M2 — Camada Web (Playwright)

## Problem Statement

O robô precisa injetar dados em formulários web multi-etapa sem nunca hardcodar seletores no código. Hoje não existe nenhum módulo `web/` — precisamos construir do zero a capacidade de: (1) abrir o navegador reaproveitando sessão persistida (sem relogin a cada execução), (2) navegar páginas com espera por carregamento assíncrono, (3) preencher formulários via mapeamento chave → seletor carregado de `config/selectors.json`, e (4) capturar o ID de transação ao final. Sem essa camada, nenhum dado extraído pelo módulo Desktop pode ser entregue ao sistema web alvo.

## Goals

- [ ] Módulo `web/` funcional: browser com sessão persistida cross-platform (macOS + Windows)
- [ ] `config/selectors.json` como única fonte de verdade para seletores DOM — zero seletor no código Python
- [ ] `fill_form(page, data)` mapeia chaves de dados para seletores e preenche campos
- [ ] Tratamento nativo de modais/pop-ups e carregamento assíncrono
- [ ] 100% dos caminhos de código cobertos por testes unitários com mocks (sem browser real)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rotinas reais de automação | M5 — depende de mapeamento da plataforma Consigaz |
| Camada de inteligência (LLM) | M3 |
| Fluxo de primeiro login | Executado manualmente pelo operador; o módulo detecta sessão expirada e lança exceção |
| Preenchimento de CAPTCHA | Fora do escopo v1 — mitigação via cabeçalhos humanos |
| Download de arquivos / upload | Não identificado no happy path atual |
| Multi-aba / multi-janela | Complexidade não justificada antes da rotina-piloto |

---

## User Stories

### P1: Sessão Persistente ⭐ MVP

**User Story**: Como orquestrador, quero que o browser abra com a sessão salva de um login anterior, para que o robô não precise fazer login a cada execução.

**Why P1**: Sem sessão persistida, o fluxo exige credenciais a cada execução — impraticável em execução agendada.

**Acceptance Criteria**:

1. WHEN `open_browser()` é chamado THEN SHALL iniciar `chromium` com `launch_persistent_context(user_data_dir=profile_path)`
2. WHEN `open_browser()` é chamado em macOS THEN `profile_path` SHALL ser `~/.consigaz-robo/playwright-profile/`
3. WHEN `open_browser()` é chamado em Windows THEN `profile_path` SHALL ser `%USERPROFILE%\.consigaz-robo\playwright-profile\`
4. WHEN perfil não existe no disco THEN SHALL ser criado automaticamente (primeiro uso)
5. WHEN página após abertura corresponde a URL de login THEN SHALL lançar `LoginRequiredError` com URL atual
6. WHEN `open_browser()` é chamado THEN SHALL aplicar cabeçalhos humanos: `user_agent`, `viewport`, `locale` configuráveis via `settings`
7. WHEN `close_browser()` é chamado THEN SHALL fechar contexto e liberar recursos (sem processo órfão)

**Independent Test**: `pytest tests/web/test_session.py` — mocks de `playwright.async_api` ou `playwright.sync_api`; sem browser real.

---

### P1: Seletores e Mapeamento ⭐ MVP

**User Story**: Como módulo Web, quero carregar todos os seletores DOM de um arquivo JSON externo, para que mudanças de layout da plataforma alvo sejam corrigíveis sem tocar no código Python.

**Why P1**: Requisito arquitetural do PRD — "mudança de layout deve ser corrigível sem tocar na lógica".

**Acceptance Criteria**:

1. WHEN `load_selectors(path)` é chamado THEN SHALL carregar e retornar o JSON como `dict[str, dict[str, str]]`
2. WHEN arquivo não existe THEN SHALL lançar `FileNotFoundError` com path completo
3. WHEN JSON está malformado THEN SHALL lançar `SelectorLoadError` com mensagem descritiva
4. WHEN `get_selector(page, key)` é chamado e `page` existe mas `key` não existe THEN SHALL lançar `SelectorNotFoundError(page=page, key=key)`
5. WHEN `get_selector(page, key)` é chamado e `page` não existe THEN SHALL lançar `SelectorNotFoundError(page=page, key=key)`
6. WHEN `load_selectors()` é chamado sem argumento THEN SHALL usar path padrão `config/selectors.json` relativo à raiz do projeto

**Independent Test**: `pytest tests/web/test_selectors.py` — usa arquivos JSON temporários (tmp_path do pytest).

---

### P1: Navegação e Formulários ⭐ MVP

**User Story**: Como módulo Web, quero navegar para uma URL, esperar carregamento, preencher formulários via mapeamento e capturar o ID de transação, para que dados do desktop sejam injetados no sistema web.

**Why P1**: É o objetivo central do M2 — sem isso nenhuma rotina pode fechar o ciclo Desktop → Web.

**Acceptance Criteria**:

1. WHEN `navigate_to(url)` é chamado THEN SHALL aguardar `networkidle` com timeout de 30s
2. WHEN página não carrega em 30s THEN SHALL lançar `PageLoadTimeoutError(url=url, elapsed=elapsed)`
3. WHEN `wait_for_selector(page, key, timeout=15)` é chamado THEN SHALL aguardar seletor ficar visível
4. WHEN seletor não aparece em `timeout` segundos THEN SHALL lançar `SelectorNotFoundError` com page + key
5. WHEN `fill_form(page, data)` é chamado THEN SHALL para cada chave em `data`: obter seletor via `get_selector(page, key)`, limpar campo, digitar valor
6. WHEN `fill_form` encontra campo do tipo `<select>` THEN SHALL usar `select_option()` em vez de `fill()`
7. WHEN `handle_modal()` é chamado THEN SHALL procurar botão de fechar (`[aria-label*='fechar']`, `button:has-text('OK')`, `button:has-text('Fechar')`) e clicar se presente; se não encontrar, retornar sem erro
8. WHEN `capture_transaction_id(page, key)` é chamado THEN SHALL extrair texto do seletor e retornar como `str`
9. WHEN `capture_transaction_id` encontra campo vazio THEN SHALL lançar `TransactionError`
10. WHEN qualquer operação Playwright falha (TimeoutError nativa) THEN SHALL ser capturada e relançada como `WebError` com contexto

**Independent Test**: `pytest tests/web/test_navigation.py` + `pytest tests/web/test_forms.py` — mocks de `Page`, `Locator` via `unittest.mock`.

---

## Edge Cases

- WHEN `fill_form` recebe `data` com chave inexistente em `selectors.json` THEN SHALL lançar `SelectorNotFoundError` antes de tentar qualquer interação
- WHEN `navigate_to` redireciona para login THEN SHALL lançar `LoginRequiredError` (detectado por URL ou elemento sentinel)
- WHEN `fill_form` recebe valor `None` para um campo THEN SHALL pular o campo (não preencher) sem lançar exceção
- WHEN browser crasha durante operação THEN `WebError` deve ser lançada com mensagem clara (não BrowserDisconnectedError crua)
- WHEN `close_browser()` é chamado sem `open_browser()` anterior THEN SHALL ser no-op (sem exceção)
- WHEN seletor retorna múltiplos elementos THEN SHALL usar o primeiro (`.first`)

---

## Gray Areas

### GA-01: Convenção de nomenclatura de `selectors.json`

**Questão**: Como organizar as chaves no `selectors.json` — por página, por feature/rotina, ou flat?

**Contexto**: O TODO do STATE.md exigia essa definição antes de M2. A escolha afeta como `fill_form` recebe parâmetros e como operadores mantêm o arquivo.

**Opções**:
- **A — Flat namespace**: `"login_username": "input[name='user']"` — simples, sem aninhamento. Chaves longas e propensas a colisão conforme cresce.
- **B — Por rotina**: `{"cadastro": {"nome": "#nome"}}` — agrupa pelo processo de negócio. Problema: uma página pode ser usada por múltiplas rotinas.
- **C — Por página (recomendado)**: `{"login": {"username": "...", "password": "..."}, "cadastro_proposta": {"nome": "...", "cpf": "..."}}` — taxonomia estável (páginas mudam menos que rotinas), navegação natural, `fill_form(page="cadastro_proposta", data={...})` é legível.

**Recomendação**: **Opção C — Por página**. Páginas são a unidade mais estável; formulários mapeiam naturalmente para páginas; operadores conseguem encontrar seletores pelo nome da tela que estão ajustando.

**Decisão tomada (2026-05-28)**: **Opção C — Hierarquia `página > elemento`**. `selectors.json` organizado como `dict[str, dict[str, str]]` onde chave de topo é o nome da página e sub-chaves são nomes de elementos. `fill_form(page, data)` recebe nome da página para lookup. Operador adiciona nova página com seu bloco; chaves de elemento usam snake_case semântico (`nome_titular`, `cpf`, `btn_avancar`).

---

### GA-02: Modo headless vs. headed

**Questão**: O browser deve rodar headless (sem janela) por padrão?

**Contexto**: Headless é mais eficiente para execução automatizada. Mas alguns sistemas detectam e bloqueiam headless. Cabeçalhos humanos ajudam, mas não eliminam o risco.

**Opções**:
- **A — Headless padrão**: mais eficiente, configurável via env var para headed quando necessário.
- **B — Headed padrão**: mais compatível com sistemas anti-bot, porém requer display (X11/VNC em servidores).

**Recomendação**: **Opção A** com `HEADLESS=false` como escape hatch via `.env`. Em v1 o robô roda em máquina dedicada com display, então headed funciona. Headless pode ser ligado quando confirmado que o sistema alvo não detecta.

**Decisão tomada (2026-05-28)**: `headless=False` como padrão (máquina dedicada com display). Configurável via `settings.web_headless: bool = False`. Ajustável em `.env` sem alterar código.

---

### GA-03: Detecção de sessão expirada

**Questão**: Como o módulo detecta que a sessão foi perdida (cookie expirado, redirect para login)?

**Contexto**: Sem detecção, o robô silenciosamente falha ao tentar preencher o formulário de login em vez do formulário de dados — erro difícil de diagnosticar.

**Opções**:
- **A — Verificar URL após navegação**: se URL contém padrões de login (`/login`, `/auth`, `/signin`) → `LoginRequiredError`.
- **B — Verificar elemento sentinel**: após `navigate_to`, checar se elemento DOM exclusivo da sessão autenticada existe (configurável em `selectors.json` como `"_session_sentinel"`).
- **C — Combinação A + B (recomendado)**: URL check é rápido e cobre a maioria dos casos; sentinel element é fallback para sistemas que não mudam URL no redirect.

**Recomendação**: **Opção C**. Implementar ambos com lógica `OR`: se URL bate padrão de login OU sentinel não encontrado → `LoginRequiredError`.

**Decisão tomada (2026-05-28)**: Opção C. Padrões de URL de login configuráveis em `settings.web_login_url_patterns: list[str]`. Sentinel configurável como chave especial `_session_sentinel` em `selectors.json` (opcional — se ausente, só URL check).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|---|---|---|---|
| WEB-01 | P1: `open_browser()` com `launch_persistent_context` | Design | Pending |
| WEB-02 | P1: `profile_path` cross-platform (`~/.consigaz-robo/playwright-profile/`) | Design | Pending |
| WEB-03 | P1: Cabeçalhos humanos (user_agent, viewport, locale) | Design | Pending |
| WEB-04 | P1: Reutilização de cookies existentes (sem relogin) | Design | Pending |
| WEB-05 | P1: `LoginRequiredError` quando sessão expirada | Design | Pending |
| WEB-06 | P1: `load_selectors(path)` carrega JSON | Design | Pending |
| WEB-07 | P1: `SelectorNotFoundError` para chave/página ausente | Design | Pending |
| WEB-08 | P1: `SelectorLoadError` para JSON malformado | Design | Pending |
| WEB-09 | P1: `navigate_to(url)` com espera por `networkidle` | Design | Pending |
| WEB-10 | P1: `PageLoadTimeoutError` após 30s | Design | Pending |
| WEB-11 | P1: `wait_for_selector(page, key, timeout=15)` | Design | Pending |
| WEB-12 | P1: `fill_form(page, data)` via mapeamento JSON | Design | Pending |
| WEB-13 | P1: `fill_form` usa `select_option` para `<select>` | Design | Pending |
| WEB-14 | P1: `handle_modal()` fecha pop-ups se presentes | Design | Pending |
| WEB-15 | P1: `capture_transaction_id(page, key)` retorna str | Design | Pending |
| WEB-16 | P1: `TransactionError` quando campo vazio | Design | Pending |
| WEB-17 | P1: `WebError` como base exception do módulo | Design | Pending |
| WEB-18 | P1: `close_browser()` fecha contexto; no-op se não aberto | Design | Pending |
| WEB-19 | P1: `headless` configurável via settings (padrão `False`) | Design | Pending |
| WEB-20 | P1: Detecção de sessão expirada por URL + sentinel (GA-03) | Design | Pending |

**Coverage:** 20 total, 0 mapeados a tasks, 20 unmapped ⚠️

---

## Success Criteria

- [ ] `pytest tests/web/` passa 100% sem browser real (todos mocks)
- [ ] `mypy src/web/` retorna zero erros (strict mode)
- [ ] `ruff check src/web/` limpo
- [ ] Nenhum seletor CSS/XPath/text hardcoded em nenhum arquivo Python de `src/web/`
- [ ] `config/selectors.json` existe com estrutura `{page: {key: selector}}`
- [ ] `open_browser()` sem sessão prévia lança `LoginRequiredError` (coberto por mock)
