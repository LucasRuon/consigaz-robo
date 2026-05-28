# M1 — Camada Desktop com Abstração de Plataforma

## Problem Statement

O robô precisa interagir com um app desktop (macOS e Windows) sem coordenadas hardcoded. Hoje não existe nenhum módulo `desktop/` — precisamos construir do zero a capacidade de: (1) lançar/focar o app alvo por plataforma, (2) esperar elementos aparecerem via ancoragem visual (OpenCV), e (3) executar ações primitivas (clicar, digitar, extrair texto via clipboard). Sem essa camada, nenhuma rotina real pode ser implementada.

## Goals

- [ ] Módulo `desktop/` funcional em macOS e Windows com abstração de plataforma completa
- [ ] `wait_for_template()` com polling confiável e timeout de 15s (NFR: nunca usa `time.sleep` estático)
- [ ] Interações primitivas (click, type, clear, extract) com zero coordenadas hardcoded
- [ ] 100% dos caminhos de código cobertos por testes unitários com mocks (sem depender de hardware)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rotinas reais de automação | M5 — depende de templates capturados do app alvo real |
| Módulo Web (Playwright) | M2 |
| Camada de inteligência (LLM) | M3 |
| Captura de templates de imagem (`.png`) | Feito manualmente pelo operador; apenas o mecanismo de leitura é implementado aqui |
| Multi-monitor / DPI scaling | Complexidade não justificada antes da rotina-piloto |

---

## User Stories

### P1: Abstração de Plataforma ⭐ MVP

**User Story**: Como orquestrador, quero lançar e focar o app alvo usando a API nativa da plataforma, para que o mesmo código funcione em macOS e Windows sem condicionais espalhados.

**Why P1**: Nenhuma outra funcionalidade do Desktop pode rodar sem primeiro ter o app em foco.

**Acceptance Criteria**:

1. WHEN `sys.platform == "darwin"` THEN `get_platform_adapter()` SHALL retornar instância de `MacAdapter`
2. WHEN `sys.platform == "win32"` THEN `get_platform_adapter()` SHALL retornar instância de `WindowsAdapter`
3. WHEN `MacAdapter.launch_app("Nome do App")` é chamado THEN SHALL executar `open -a "Nome do App"` via subprocess
4. WHEN `MacAdapter.focus_window("Nome do App")` é chamado THEN SHALL executar AppleScript `tell application "Nome do App" to activate`
5. WHEN `MacAdapter.modifier_key()` é chamado THEN SHALL retornar `"command"`
6. WHEN `WindowsAdapter.modifier_key()` é chamado THEN SHALL retornar `"ctrl"`
7. WHEN `WindowsAdapter.focus_window("Nome")` é chamado THEN SHALL usar `pygetwindow` para trazer janela ao foco
8. WHEN qualquer adapter falha (processo não encontrado, janela não existe) THEN SHALL lançar `PlatformError` com mensagem descritiva

**Independent Test**: Rodar `pytest tests/desktop/test_platform_adapters.py` — todos os métodos testados com mock de subprocess/pygetwindow, sem abrir nenhum app real.

---

### P1: Ancoragem Visual (OpenCV) ⭐ MVP

**User Story**: Como módulo Desktop, quero esperar um elemento aparecer na tela via template matching, para que nunca haja `time.sleep` estático (requisito NFR-5.1).

**Why P1**: Todas as interações primitivas dependem de `wait_for_template()` para localizar a posição exata antes de agir.

**Acceptance Criteria**:

1. WHEN `wait_for_template(path, timeout=15, threshold=0.8)` é chamado e o template aparece antes do timeout THEN SHALL retornar `(x, y)` do centro do match
2. WHEN o template não aparece dentro de `timeout` segundos THEN SHALL salvar screenshot em `logs/errors/<timestamp>_<routine>.png` e lançar `TemplateNotFoundError`
3. WHEN `threshold` não é passado THEN SHALL usar `0.8` como default
4. WHEN o arquivo de template não existe THEN SHALL lançar `FileNotFoundError` antes de tentar capturar screenshot
5. WHEN múltiplos matches são encontrados THEN SHALL retornar o de maior score (`cv2.TM_CCOEFF_NORMED`)
6. WHEN chamado THEN SHALL fazer polling com intervalo de `0.5s` (não bloquear CPU continuamente)

**Independent Test**: Rodar `pytest tests/desktop/test_vision.py` com mocks de `pyautogui.screenshot()` e `cv2.matchTemplate()` — simular match imediato, timeout, arquivo ausente.

---

### P1: Interações Primitivas ⭐ MVP

**User Story**: Como módulo Desktop, quero executar click, digitação, limpeza de campo e extração de texto via clipboard sobre posições identificadas por template matching, para que zero coordenadas hardcoded existam no código.

**Why P1**: São os blocos construtivos de qualquer rotina de automação.

**Acceptance Criteria**:

1. WHEN `click_at_template(path)` é chamado THEN SHALL chamar `wait_for_template(path)` e depois `pyautogui.click(x, y)` com as coordenadas retornadas
2. WHEN `type_text(text)` é chamado THEN SHALL usar `pyautogui.write(text, interval=0.05)` (não `typewrite` raw — evita perda de caracteres)
3. WHEN `clear_field()` é chamado THEN SHALL selecionar tudo (`modifier_key + A`) e deletar
4. WHEN `extract_via_clipboard()` é chamado THEN SHALL selecionar tudo, copiar (`modifier_key + C`), ler `pyperclip.paste()` e retornar o texto
5. WHEN qualquer ação de UI falha (exceção de pyautogui) THEN SHALL lançar `InteractionError` com contexto (qual ação, qual template)
6. WHEN qualquer primitiva é chamada THEN SHALL estar envolta em `try/except` obrigatório (NFR-5.2)

**Independent Test**: Rodar `pytest tests/desktop/test_interactions.py` com mock de `pyautogui` e `pyperclip`.

---

## Edge Cases

- WHEN o app alvo trava durante `wait_for_template` THEN SHALL respeitar o timeout de 15s e salvar screenshot antes de lançar exceção
- WHEN `type_text("")` é chamado (string vazia) THEN SHALL ser no-op (sem chamar pyautogui)
- WHEN template existe mas `threshold` está alto demais (0.99) e não há match perfeito THEN SHALL tratar como timeout
- WHEN `extract_via_clipboard()` retorna string vazia THEN SHALL retornar `""` sem lançar exceção
- WHEN `get_platform_adapter()` é chamado em Linux THEN SHALL lançar `UnsupportedPlatformError`

---

## Gray Areas

### GA-01: Organização dos templates de imagem

**Questão**: Templates ficam em pasta única (`assets/templates/`) ou separados por SO (`assets/templates/darwin/`, `assets/templates/win32/`)?

**Contexto**: Elementos de UI podem ter aparência diferente entre macOS e Windows (fontes, cores, bordas). Se um template capturado no mac não faz match no Windows (e vice-versa), a pasta única quebra silenciosamente.

**Opções**:
- **A — Pasta única** `assets/templates/`: mais simples, assume que as UIs são idênticas entre SOs. Se divergirem, o template do SO atual sobrescreve o do outro.
- **B — Separado por SO** `assets/templates/{darwin,win32}/`: cada SO tem seus próprios templates; `wait_for_template()` insere o subdiretório correto automaticamente. Mais robusto, custo: dois conjuntos de templates para manter.
- **C — Pasta única com fallback**: busca primeiro em `assets/templates/{platform}/`, se não encontrar cai em `assets/templates/`. Máxima flexibilidade.

**Recomendação**: **Opção C** (fallback). Permite começar com pasta única (menos overhead operacional no piloto) e adicionar templates SO-específicos apenas quando necessário, sem refatorar código.

**Decisão tomada (2026-05-28)**: **Opção C — Fallback por SO**. `wait_for_template()` busca primeiro em `assets/templates/{sys.platform}/`, depois em `assets/templates/`. Operador salva em pasta raiz por padrão; move para subpasta de SO apenas quando a UI divergir.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|---|---|---|---|
| DESK-01 | P1: Factory `get_platform_adapter()` | Design | Pending |
| DESK-02 | P1: `MacAdapter.launch_app` + `focus_window` | Design | Pending |
| DESK-03 | P1: `WindowsAdapter.launch_app` + `focus_window` | Design | Pending |
| DESK-04 | P1: `modifier_key()` por plataforma | Design | Pending |
| DESK-05 | P1: `PlatformError` em falha de adapter | Design | Pending |
| DESK-06 | P1: `wait_for_template()` retorna `(x, y)` | Design | Pending |
| DESK-07 | P1: Timeout → screenshot + `TemplateNotFoundError` | Design | Pending |
| DESK-08 | P1: Polling com intervalo de 0.5s | Design | Pending |
| DESK-09 | P1: Fallback de templates por SO (GA-01) | Design | Pending |
| DESK-10 | P1: `click_at_template()` | Design | Pending |
| DESK-11 | P1: `type_text()` com interval | Design | Pending |
| DESK-12 | P1: `clear_field()` via modifier_key | Design | Pending |
| DESK-13 | P1: `extract_via_clipboard()` via pyperclip | Design | Pending |
| DESK-14 | P1: `try/except` obrigatório em todas as primitivas | Design | Pending |
| DESK-15 | P1: `UnsupportedPlatformError` em plataformas desconhecidas | Design | Pending |

**Coverage:** 15 total, 0 mapeados a tasks, 15 unmapped ⚠️

---

## Success Criteria

- [ ] `pytest tests/desktop/` passa 100% sem hardware real (todos mocks)
- [ ] `mypy src/desktop/` retorna zero erros (strict mode)
- [ ] `ruff check src/desktop/` limpo
- [ ] Nenhuma coordenada hardcoded em nenhum arquivo de `src/desktop/`
- [ ] `wait_for_template()` nunca usa `time.sleep` estático — polling com `asyncio.sleep` ou loop com `time.monotonic()`
