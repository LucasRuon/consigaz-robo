# Spec — `pilot-smoke` (M5)

**Milestone:** M5 — Primeira Rotina End-to-End
**Tipo:** Rotina-esqueleto (smoke E2E)
**Status:** Specified — 2026-05-28

## Resumo

`pilot-smoke` é a primeira rotina **real** registrada em `src/routines/` e exercita as quatro
camadas do robô (Desktop → Inteligência → Web → Orquestrador) ponta a ponta usando alvos
neutros e disponíveis em qualquer máquina. Não automatiza nenhum processo de negócio Consigaz —
seu único objetivo é **provar que o chassis cabeado em M0-M4 funciona em execução real**, de
forma que a rotina TOTVS de produção (M6+) possa ser implementada substituindo apenas
templates, seletores, schemas e prompts, sem mudar o pipeline.

**Alvos:**

- Desktop: **Calculadora nativa** (`Calculator.app` no macOS, `calc.exe` no Windows) — escolhida
  por estar pré-instalada nos dois SOs e oferecer UI estável (boa para template matching).
- Web: **`https://httpbin.org/forms/post`** — formulário HTML público, sem login, com submit
  que ecoa os dados em JSON (verificação trivial de sucesso).
- LLM: OpenAI (modelo configurado em `settings.llm_default_model`) classificando uma
  observação textual fixa.

## Por que esta rotina existe

Sem `pilot-smoke`, M0-M4 entregam infraestrutura sem **uma única execução real comprovando
que os contratos entre camadas funcionam fora dos testes unitários**. Casos concretos que só
aparecem em E2E:

- O `RoutineContext` injetado pelo `dispatch` carrega o `logger` correto e a `evidence`
  acumulada chega no `execution_summary`.
- `intelligence.reset_for_new_execution(settings)` realmente zera o `CostTracker` entre runs.
- `wait_for_template` encontra um template real capturado da Calculadora nativa.
- Playwright reusa o profile persistido entre execuções (segundo run sai mais rápido).
- A cadeia `validate → call_llm → decide → web.fill_form → web.submit` executa sem
  glue-code ausente.

Quando essa rotina passar verde em macOS, M6 (TOTVS) começa com confiança de que o pipeline
está sólido — qualquer falha em M6 será no domínio (templates TOTVS, fluxo Consigaz), não no
chassis.

## Escopo

### Inclui (v1 desta rotina)

- Rotina registrada como `@register("pilot-smoke")` em `src/routines/pilot_smoke.py`.
- Templates de imagem para Calculadora (macOS + Windows) em
  `assets/templates/pilot-smoke/{darwin,win32}/`.
- Schema de validação `PilotSmokeData` em `src/intelligence/schemas/pilot_smoke.py`
  registrado via `@register("pilot-smoke")`.
- Prompt da LLM em `config/prompts/pilot-smoke.md` com frontmatter YAML e
  `response_schema: pilot-smoke-llm`.
- Bloco de seletores `pilot_smoke` em `config/selectors.json` mapeando os campos do
  formulário httpbin.
- Suporte a `--dry-run`: executa desktop + validação + LLM, mas **não** clica em Submit no
  Playwright.
- Teste E2E pulável (`pytest -m e2e`) que executa a rotina inteira em macOS quando a flag
  `RUN_E2E_PILOT_SMOKE=1` está presente.
- Testes unitários da rotina (estrutura, contrato com `RoutineContext`) sem precisar de
  Calculadora real (mocks).

### Não inclui

- Automação de qualquer processo Consigaz real.
- Suporte a TOTVS (sai em M6).
- Captura de novos templates por OCR/visão — templates ficam versionados como `.png` no repo.
- Validação automática do conteúdo do JSON retornado por httpbin (basta o status 200 e
  evidence registrar a URL final).
- Execução E2E em Windows como gate de M5 — Windows continua bloqueado pelo mesmo motivo
  de M0 (sem máquina disponível) e fica como checklist manual em `CHECKS.md`.

## Requisitos

### Funcionais (FR)

**FR-1 — Registro e descoberta**

- **FR-1.1** A rotina é descoberta automaticamente pelo auto-discovery de `src/routines/`
  implementado em M4, sem edição da CLI nem do registry.
- **FR-1.2** `python -m orchestrator --list` exibe `pilot-smoke` na lista.
- **FR-1.3** `python -m orchestrator --routine pilot-smoke` executa a rotina com exit code
  mapeado por M4 conforme a `Action` retornada.

**FR-2 — Camada Desktop**

- **FR-2.1** A rotina abre a Calculadora nativa via `PlatformAdapter.launch_app` e traz para
  foco via `PlatformAdapter.focus_window`. Em macOS usa o nome `Calculator`; em Windows usa
  `calc.exe`. Ambos resolvidos via fallback em `assets/templates/pilot-smoke/{darwin,win32}/`
  (GA-01).
- **FR-2.2** A rotina digita a operação `2 + 3` (sequência de cliques em templates dos botões
  `2`, `+`, `3`, `=`) e captura o resultado via `extract_via_clipboard()`.
- **FR-2.3** Toda espera por UI usa `wait_for_template(timeout=15s)` — proibido `time.sleep`
  estático (mantém invariante do PRD).
- **FR-2.4** Em qualquer falha de template matching, screenshot é salvo em
  `logs/errors/<timestamp>_pilot-smoke.png` (já implementado no logger M0) e a exceção
  customizada do módulo desktop propaga para o orquestrador.

**FR-3 — Camada de Inteligência**

- **FR-3.1** Schema `PilotSmokeData` em `intelligence/schemas/pilot_smoke.py` valida o dict
  extraído com campos `operation: str` (regex `^\d+\s*[+\-*/]\s*\d+$`), `result: int`,
  `observation: str` (free text fixo na v1: `"cálculo de teste end-to-end"`).
- **FR-3.2** Validação roda **antes** da chamada LLM (economia de tokens, invariante M3).
- **FR-3.3** O prompt `pilot-smoke.md` recebe `{operation}`, `{result}`, `{observation}` como
  placeholders e retorna `PilotSmokeLLM` (`decision: Literal["approve","reject","escalate"]`,
  `confidence: float`, `summary: str` com até 200 chars resumindo a observação).
- **FR-3.4** `intelligence.router.decide(structured, llm_result)` é chamada e retorna
  `Decision`. Resultado esperado em condições normais: `Action.PROCEED_TO_WEB` com
  `confidence >= settings.llm_min_confidence`.
- **FR-3.5** Se `decide()` retornar `Action.RAISE_EXCEPTION` por baixa confiança, a rotina
  encerra com a exceção apropriada (orquestrador mapeia para exit code 4).

**FR-4 — Camada Web**

- **FR-4.1** A rotina abre Playwright com o profile persistente padrão e navega para
  `https://httpbin.org/forms/post`.
- **FR-4.2** Os seletores ficam em `config/selectors.json` sob a chave `pilot_smoke` com
  sub-chaves para os campos do formulário httpbin (`custname`, `custtel`, `custemail`,
  `comments`, `submit`). Zero seletor hardcoded em código (invariante M2).
- **FR-4.3** A rotina chama `fill_form("pilot_smoke", data)` com:
  - `custname`: `"pilot-smoke"`
  - `custtel`: `"+55-00-0000-0000"`
  - `custemail`: `"pilot-smoke@example.invalid"`
  - `comments`: `f"{operation} = {result} | {llm_summary}"`
- **FR-4.4** Em modo normal, clica em `submit` e aguarda a página de resposta.
- **FR-4.5** Em `--dry-run`, **não** clica em submit — sai imediatamente com
  `RoutineResult(action=PROCEED_TO_WEB, evidence={"dry_run": True, "filled_fields": [...]})`.

**FR-5 — Orquestrador / Resultado**

- **FR-5.1** Sucesso retorna `RoutineResult(action=PROCEED_TO_WEB, evidence={...})` com
  `evidence` contendo apenas chaves seguras (sem PII, sem segredos): `operation`, `result`,
  `llm_decision`, `llm_confidence`, `web_final_url`, `web_status`.
- **FR-5.2** O `execution_summary` emitido pelo dispatch contém `routine="pilot-smoke"`,
  `tokens_in`, `tokens_out`, `cost_usd`, `duration_s`, `evidence_keys` ordenadas. Nenhum
  valor de `evidence` aparece no summary (invariante M4).

### Não-funcionais (NFR)

- **NFR-1** Retry exponencial (`tenacity`) nas chamadas HTTP (LLM via M3, Playwright via M2).
- **NFR-2** Templates novos da Calculadora capturados em alta resolução com tolerância
  `threshold=0.85` (default seguro do `wait_for_template`).
- **NFR-3** Sem segredos no log/screenshot (já garantido pelo sanitizador M0).
- **NFR-4** Cold-start: importar `src.routines.pilot_smoke` não carrega Pandas (helpers
  `intelligence.analysis` permanecem opt-in — esta rotina não precisa).
- **NFR-5** Custo por execução em produção: cap de tokens via `settings.llm_token_hard_cap`
  default; LLM recebe prompt curto (<500 tokens) + resposta pequena (<200 tokens). Custo
  esperado: < $0.01 por run.

### Critérios de aceite (gate de M5)

- **AC-1** `pytest` passa (todos os 377+ testes existentes verdes; novos testes unitários
  desta rotina verdes; teste E2E pulável quando `RUN_E2E_PILOT_SMOKE` ausente).
- **AC-2** `ruff check src/` e `mypy src/routines/ src/intelligence/schemas/pilot_smoke.py`
  limpos.
- **AC-3** `python -m orchestrator --list` mostra `pilot-smoke`.
- **AC-4** Em macOS com `OPENAI_API_KEY` válida, `RUN_E2E_PILOT_SMOKE=1 python -m orchestrator
  --routine pilot-smoke` executa fim-a-fim com exit code 0 e um único `execution_summary`
  em `logs/*.json` com `action="proceed_to_web"` e `tokens_in > 0`.
- **AC-5** O mesmo comando com `--dry-run` executa sem abrir Playwright em modo de submit
  e sai com `evidence.dry_run=true` no summary's `evidence_keys`.
- **AC-6** Em uma execução com `OPENAI_API_KEY` inválida, a rotina falha com exit code 3
  (LLM error) e `error_type` no summary.
- **AC-7** Checklist Windows adicionado em `CHECKS.md` (seção M5) descrevendo como executar
  manualmente quando uma máquina Windows estiver disponível — não bloqueia o fechamento de
  M5 como `done` em macOS.

## Gray areas resolvidas nesta sessão

1. **Escopo de M5**: rotina-esqueleto smoke (M5-A) em vez de rotina TOTVS real — TOTVS sai
   em M6 quando o produto/telas/processo forem mapeados.
2. **Alvo desktop**: Calculadora nativa (presente em ambos SOs, estável visualmente) em vez
   de TOTVS (não disponível agora).
3. **Alvo web**: `httpbin.org/forms/post` (público, sem login, resposta determinística).
4. **Observação para LLM**: string fixa na v1 (`"cálculo de teste end-to-end"`). A rotina
   ainda exercita o caminho LLM completo, mas o conteúdo não vem de free text real do
   desktop — manter realista o mínimo para o smoke.

## Dependências e bloqueios

- **Depende de:** M0 (config, logging), M1 (PlatformAdapter, wait_for_template), M2
  (Playwright + fill_form + selectors.json), M3 (validation, llm, router, schemas,
  prompts), M4 (registry, dispatch, summary). Todos concluídos.
- **Não depende de:** mapeamento TOTVS (intencional).
- **Bloqueador remanescente para Windows:** ausência de máquina — herdado de M0.

## Próximos passos

1. Confirmar spec.
2. Avaliar necessidade de `design.md`: provavelmente **dispensável** — não há decisão
   arquitetural nova (apenas consumir contratos já decididos em M0-M4). Mas há valor em
   um `design.md` curto documentando a sequência exata do pipeline e o formato do
   `evidence`, para servir de template ao M6.
3. Quebrar em `tasks.md` (estimativa: 6-8 tasks — schema, prompt, selectors, templates,
   código da rotina, testes unit, teste E2E pulável, checklist Windows).
4. Executar.
