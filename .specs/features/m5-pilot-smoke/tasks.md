# Tasks — `pilot-smoke` (M5)

**Feature:** `m5-pilot-smoke`
**Status:** Ready to execute — 2026-05-29
**Total:** 9 tasks (8 código + 1 housekeeping)

## Convenções

- **[P]** = paralelizável (sem dependência mútua na mesma onda).
- Cada task = 1 commit atômico no padrão Conventional Commits.
- Gate por task: `pytest`, `ruff check src/`, `mypy <paths-tocados>` verdes.
- `Done when` é o critério objetivo; `Tests` é o que deve passar.

## Ordem de execução (waves)

```
Wave 1 (sequencial)     │  T01 (schemas)
Wave 2 (paralelo) [P]   │  T02 (prompt)  │  T03 (selectors)  │  T04 (templates)
Wave 3 (sequencial)     │  T05 (rotina)
Wave 4 (paralelo) [P]   │  T06 (testes unit)  │  T07 (teste E2E gateado)
Wave 5 (sequencial)     │  T08 (CHECKS Windows)
Wave 6 (sequencial)     │  T09 (atualização STATE + ROADMAP)
```

---

## T01 — Schemas Pydantic para `pilot-smoke`

**What:** Criar os schemas `PilotSmokeData` (extração desktop) e `PilotSmokeLLM` (resposta da LLM), registrados no registry de schemas.

**Where:** `src/intelligence/schemas/pilot_smoke.py` (novo arquivo).

**Depends on:** —

**Reuses:** `intelligence.schemas.register`, `intelligence.types`, `pydantic.BaseModel`.

**Cobre:** FR-3.1, FR-3.3.

**Done when:**

- Arquivo existe com `PilotSmokeData` (operation regex `^\d+\s*[+\-*/]\s*\d+$`, result int, observation 1-500 chars) e `PilotSmokeLLM` (decision Literal, confidence 0-1, summary 1-200 chars).
- Ambos registrados via `@register("pilot-smoke")` e `@register("pilot-smoke-llm")`.
- `from intelligence.schemas import get_schema; get_schema("pilot-smoke-llm")` resolve para a classe.

**Tests:** `tests/test_intelligence/test_schemas_pilot_smoke.py` (novo) — 4 testes: registro, validação OK, regex rejeita `"abc"`, confidence fora de [0,1] rejeitada.

**Gate:** `pytest tests/test_intelligence/test_schemas_pilot_smoke.py && ruff check src/intelligence/schemas/pilot_smoke.py && mypy src/intelligence/schemas/pilot_smoke.py`.

**Commit:** `feat(intelligence): schemas Pydantic para rotina pilot-smoke [T01]`

---

## T02 [P] — Prompt LLM versionado

**What:** Criar o prompt da rotina em Markdown com frontmatter YAML (versão 1, response_schema `pilot-smoke-llm`).

**Where:** `config/prompts/pilot-smoke.md` (novo arquivo).

**Depends on:** T01 (precisa do schema registrado para `prompts.load` validar `response_schema`).

**Reuses:** Convenção de frontmatter definida em M3 ([[m3-prompts-frontmatter]]).

**Cobre:** FR-3.3.

**Done when:**

- Arquivo existe com frontmatter (`version: 1`, `temperature: 0.0`, `response_schema: pilot-smoke-llm`, `model` opcional).
- Corpo usa placeholders `{operation}`, `{result}`, `{observation}`.
- `intelligence.prompts.load("pilot-smoke")` retorna sem erro.
- `.render(operation="2+3", result=5, observation="x")` retorna `RenderedPrompt` válido.

**Tests:** `tests/test_intelligence/test_prompts_pilot_smoke.py` (novo) — 3 testes: load OK, render OK, render com placeholder ausente lança `PromptRenderError`.

**Gate:** `pytest tests/test_intelligence/test_prompts_pilot_smoke.py && ruff check src/`.

**Commit:** `feat(prompts): prompt pilot-smoke v1 com response_schema [T02]`

---

## T03 [P] — Bloco de seletores web

**What:** Adicionar bloco `pilot_smoke` em `config/selectors.json` mapeando campos do formulário httpbin.

**Where:** `config/selectors.json` (edição — preservar blocos existentes).

**Depends on:** —

**Reuses:** Convenção `selectors.json` ([[m2-selectors-convention]]) — chave de página + sub-chaves de elementos + `_session_sentinel`.

**Cobre:** FR-4.2.

**Done when:**

- Bloco `pilot_smoke` presente com chaves: `_session_sentinel`, `custname`, `custtel`, `custemail`, `comments`, `submit` (todos seletores CSS do form real do httpbin).
- JSON válido (passa em `python -c "import json; json.load(open('config/selectors.json'))"`).
- Nenhum bloco existente alterado.

**Tests:** `tests/test_config/test_selectors_pilot_smoke.py` (novo) — 2 testes: chave existe, todos os elementos esperados presentes.

**Gate:** `pytest tests/test_config/test_selectors_pilot_smoke.py`.

**Commit:** `feat(config): bloco pilot_smoke em selectors.json (httpbin) [T03]`

---

## T04 [P] — Templates de imagem da Calculadora (macOS)

**What:** Capturar templates `.png` da Calculadora nativa do macOS para os botões usados (`2`, `3`, `+`, `=`) e a âncora de janela.

**Where:** `assets/templates/pilot-smoke/darwin/{window_titlebar,btn_2,btn_3,btn_plus,btn_equals}.png`.

**Depends on:** —

**Reuses:** Estratégia GA-01 — `darwin/` primeiro; raiz só se idêntico em ambos SOs.

**Cobre:** FR-2.1, FR-2.2, FR-2.3, NFR-2.

**Done when:**

- Os 5 PNGs existem em `assets/templates/pilot-smoke/darwin/`.
- Cada arquivo < 100 KB, formato PNG válido (passa `file <path>`).
- Captura feita em tema claro, zoom nativo do display da máquina de desenvolvimento.
- Pasta `assets/templates/pilot-smoke/win32/` criada com `.gitkeep` (placeholder para futura captura Windows).

**Tests:** `tests/test_assets/test_pilot_smoke_templates.py` (novo) — verifica existência e formato dos 5 templates darwin + presença do `.gitkeep` em win32.

**Gate:** `pytest tests/test_assets/test_pilot_smoke_templates.py`.

**Commit:** `feat(assets): templates pilot-smoke para Calculadora macOS [T04]`

---

## T05 — Rotina `pilot-smoke` (orchestrator handler)

**What:** Implementar a rotina em si: registrar `@register("pilot-smoke")` e implementar `run(ctx)` seguindo a sequência de 21 passos do design §2.

**Where:** `src/routines/pilot_smoke.py` (novo arquivo).

**Depends on:** T01, T02, T03, T04.

**Reuses:**

- M1: `desktop.PlatformAdapter`, `desktop.wait_for_template`, `desktop.click_at_template`, `desktop.extract_via_clipboard`.
- M2: `web.open_session`, `web.fill_form`, `web.close_session`.
- M3: `intelligence.validate`, `intelligence.prompts.load`, `intelligence.call_llm`, `intelligence.router.decide`, `intelligence.reset_for_new_execution` (chamado por M4 antes da rotina).
- M4: `orchestrator.registry.register`, `orchestrator.types.{RoutineContext,RoutineResult,Action}`.

**Cobre:** FR-1.1, FR-1.2, FR-1.3, FR-2.*, FR-3.4, FR-3.5, FR-4.1, FR-4.3, FR-4.4, FR-4.5, FR-5.1, NFR-1, NFR-4.

**Done when:**

- Função `run(ctx: RoutineContext) -> RoutineResult` existe e está decorada com `@register("pilot-smoke")`.
- Auto-discovery de M4 carrega a rotina (`python -m orchestrator --list` mostra `pilot-smoke` — verificável manualmente).
- Helpers privados (`_extract_from_calculator`, `_submit_to_httpbin`, `_build_evidence`) implementados conforme design §6.
- `_build_evidence` produz exatamente as chaves do design §4 (nenhuma a mais).
- `ctx.dry_run=True` faz early-return antes de abrir Playwright; evidence contém `dry_run: True` e **não** contém `web_*`.
- Sem `time.sleep` estático; sem coordenadas hardcoded; sem seletor web hardcoded.
- Import do módulo **não** carrega Pandas (NFR-4 — checável com `python -c "import sys; import src.routines.pilot_smoke; assert 'pandas' not in sys.modules"`).

**Tests:** Cobertos por T06 (unit) e T07 (E2E). Esta task entrega a implementação; testes são tasks separadas para permitir paralelização da wave 4.

**Gate:** `ruff check src/routines/pilot_smoke.py && mypy src/routines/pilot_smoke.py && python -m orchestrator --list | grep pilot-smoke`.

**Commit:** `feat(routines): rotina pilot-smoke E2E (desktop→intel→web) [T05]`

---

## T06 [P] — Testes unitários da rotina

**What:** Implementar os 6 testes unitários listados no design §7 com mocks de desktop/web/LLM.

**Where:** `tests/test_routines/test_pilot_smoke_unit.py` (novo arquivo) + `tests/test_routines/__init__.py` se não existir.

**Depends on:** T05.

**Reuses:** Padrões de mocking de M1-M4 (fakes injetáveis via `monkeypatch`).

**Cobre:** Verificação de FR-1.*, FR-3.4, FR-3.5, FR-4.5, FR-5.1.

**Done when:**

- 6 testes implementados:
  - `test_run_invokes_pipeline_in_order`
  - `test_dry_run_skips_web_submit`
  - `test_evidence_keys_are_safe` (assert nenhum key inicia com `_`; nenhum valor é segredo conhecido)
  - `test_low_confidence_raises_exception`
  - `test_validation_failure_short_circuits` (assert LLM mock nunca chamado)
  - `test_registered_with_correct_name`
- Todos passam sem Calculadora real e sem `OPENAI_API_KEY`.
- Sem `pytest.mark.e2e` — rodam em CI.

**Gate:** `pytest tests/test_routines/test_pilot_smoke_unit.py -v && ruff check tests/test_routines/`.

**Commit:** `test(routines): testes unitários da rotina pilot-smoke [T06]`

---

## T07 [P] — Teste E2E gateado por env var

**What:** Implementar o teste end-to-end que executa a rotina real no macOS quando `RUN_E2E_PILOT_SMOKE=1`.

**Where:** `tests/test_routines/test_pilot_smoke_e2e.py` (novo arquivo).

**Depends on:** T05.

**Reuses:** `pytest.mark.skipif`, `pytest.mark.e2e` (registrar marker em `pyproject.toml` se ainda não existe).

**Cobre:** AC-4, AC-5, AC-6.

**Done when:**

- Teste `test_full_pipeline_macos` existe com `@pytest.mark.e2e` e `skipif(sys.platform != "darwin" or not os.getenv("RUN_E2E_PILOT_SMOKE") or not os.getenv("OPENAI_API_KEY"))`.
- Asserta exit code 0 (via `subprocess.run`), captura `logs/*.json` mais recente, `jq`-extrai o evento `execution_summary` e verifica `action=="proceed_to_web"`, `tokens_in > 0`, `error_type` ausente.
- Teste `test_dry_run_does_not_submit` análogo com `--dry-run`, verifica `evidence_keys` contém `dry_run` e **não** contém `web_final_url`.
- Teste `test_invalid_api_key_returns_exit_3` com env `OPENAI_API_KEY=invalid`, verifica exit code 3.
- Em CI / em ausência das vars, todos os 3 testes são `skipped` (não `failed`).
- Marker `e2e` declarado em `pyproject.toml` sob `[tool.pytest.ini_options].markers`.

**Gate:** `pytest tests/test_routines/test_pilot_smoke_e2e.py` (deve mostrar 3 skipped em CI) + `ruff check`.

**Commit:** `test(routines): teste E2E pilot-smoke gateado por env var [T07]`

---

## T08 — Checklist Windows em `CHECKS.md`

**What:** Adicionar seção M5 em `CHECKS.md` com passos manuais para validar `pilot-smoke` em Windows quando uma máquina estiver disponível.

**Where:** `CHECKS.md` (edição — adicionar seção; não alterar seções existentes).

**Depends on:** T07.

**Reuses:** Estrutura do checklist M0 (mesma convenção `[ ]` / `[x]` / `[~]`).

**Cobre:** AC-7.

**Done when:**

- Seção `## M5 — pilot-smoke (Windows)` adicionada.
- Passos: capturar templates `win32/`, instalar Calculadora (já vem com Windows), exportar `OPENAI_API_KEY`, exportar `RUN_E2E_PILOT_SMOKE=1`, rodar `python -m orchestrator --routine pilot-smoke`, verificar exit 0 e `execution_summary` no log.
- Todos os itens marcados `[ ]` (pendentes — Windows ainda não disponível, herdado de M0).

**Tests:** N/A (documentação).

**Gate:** Inspeção visual do arquivo + verificação que outras seções não foram alteradas (`git diff CHECKS.md`).

**Commit:** `docs(checks): checklist Windows para pilot-smoke (pendente máquina) [T08]`

---

## T09 — Atualização de STATE.md e ROADMAP.md

**What:** Registrar decisões de design de M5 em `STATE.md`, mover blocker resolvido, atualizar `ROADMAP.md` para `M5: DONE ✅ (macOS)`.

**Where:** `.specs/project/STATE.md` + `.specs/project/ROADMAP.md`.

**Depends on:** T01-T08.

**Reuses:** Convenção de seção `Decisions` com data + título + corpo + `How to apply` ([[state-management]]).

**Cobre:** Higiene de memória entre milestones.

**Done when:**

- Em `STATE.md > Decisions`, nova entrada `2026-05-29 — M5 concluído: chassis E2E provado via pilot-smoke` resumindo: rotina implementada, 4 camadas exercitadas em execução real macOS, contrato de `evidence` canônico fixado, templates Calculadora capturados, Windows pendente.
- Em `STATE.md > Decisions`, nova entrada `2026-05-29 — M5: contrato canônico de evidence` listando as chaves padrão e a regra "M6+ herda esse shape".
- Em `STATE.md > Blockers`, os 3 bloqueadores de M5 (app desktop, plataforma web, rotina-piloto) **substituídos** por uma única nota: `Bloqueado para M6 — mapeamento TOTVS pendente` (produto + telas + campos + processo).
- Em `STATE.md > Lessons`, entrada nova se algo não-óbvio surgiu durante a implementação (deixar em branco se não houver — não inventar).
- Em `ROADMAP.md`, marcar `## M5 — Primeira Rotina End-to-End` como `**Status:** M0-M5 concluídos ✅ (macOS) — pronto para M6`.
- Em `ROADMAP.md`, marcar feature `**Rotina-piloto**` como `DONE ✅` e adicionar nota: `Implementada como rotina-esqueleto pilot-smoke; rotina TOTVS de produção fica em M6.`
- Adicionar nova seção `## M6 — Rotina TOTVS de Produção` em `ROADMAP.md` com `Goal`, `Bloqueador: mapeamento TOTVS`, e features placeholder.

**Tests:** N/A (housekeeping).

**Gate:** `git diff` mostra apenas STATE.md + ROADMAP.md alterados; nenhum arquivo de código tocado.

**Commit:** `docs(state,roadmap): M5 concluído e M6 (TOTVS) aberto [T09]`

---

## Traceabilidade Spec ↔ Tasks

| Requisito | Coberto por |
|---|---|
| FR-1.1 (auto-discovery) | T05 |
| FR-1.2 (--list) | T05 + T06 |
| FR-1.3 (--routine + exit codes) | T05 + T07 |
| FR-2.1 (launch + focus) | T04 + T05 |
| FR-2.2 (digita 2+3 + clipboard) | T04 + T05 |
| FR-2.3 (sem time.sleep) | T05 (revisão de gate) |
| FR-2.4 (screenshot em falha) | Reusa M0 (já implementado) |
| FR-3.1 (PilotSmokeData) | T01 |
| FR-3.2 (validação antes de LLM) | T05 + T06 |
| FR-3.3 (prompt + PilotSmokeLLM) | T01 + T02 |
| FR-3.4 (decide → PROCEED_TO_WEB) | T05 + T06 |
| FR-3.5 (low confidence → exception) | T05 + T06 |
| FR-4.1 (Playwright + profile) | T05 (reusa M2) |
| FR-4.2 (selectors.json) | T03 |
| FR-4.3 (fill_form) | T05 |
| FR-4.4 (submit em modo normal) | T05 + T07 |
| FR-4.5 (dry-run skip submit) | T05 + T06 + T07 |
| FR-5.1 (evidence safe) | T05 + T06 |
| FR-5.2 (execution_summary) | Reusa M4 (já implementado); T07 verifica |
| NFR-1 (retry exponencial) | Reusa M2/M3 |
| NFR-2 (threshold templates) | T04 |
| NFR-3 (sem segredos em log) | Reusa M0 |
| NFR-4 (cold start sem pandas) | T05 (gate manual) |
| NFR-5 (cap de tokens) | Reusa M3 |
| AC-1 (pytest verde) | T06 + T07 |
| AC-2 (ruff + mypy) | T01-T07 (gate) |
| AC-3 (--list mostra rotina) | T05 |
| AC-4 (E2E exit 0) | T07 |
| AC-5 (--dry-run evidence) | T07 |
| AC-6 (API key inválida → exit 3) | T07 |
| AC-7 (CHECKS Windows) | T08 |

---

## Estimativa

- T01-T03: ~30min cada (arquivos pequenos, escopo claro).
- T04: ~20min (capturar templates manualmente na Calculadora local).
- T05: ~2h (rotina + helpers + integração das 4 camadas + revisão de gate).
- T06: ~1h (6 testes com mocks).
- T07: ~45min (3 testes E2E gateados + marker).
- T08: ~15min (documentação).
- T09: ~20min (housekeeping STATE + ROADMAP).

**Total estimado:** ~5h de trabalho efetivo (1 sessão produtiva).
