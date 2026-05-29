# Design — `pilot-smoke` (M5)

**Feature:** `m5-pilot-smoke`
**Tipo:** Rotina-esqueleto E2E
**Status:** Designed — 2026-05-29
**Depende de:** M0 (config/logging), M1 (desktop), M2 (web), M3 (intelligence), M4 (orchestrator)

> Este design é deliberadamente curto. Não há decisão arquitetural nova — `pilot-smoke`
> consome contratos já fechados em M0-M4. O valor desta página é **fixar a sequência
> exata do pipeline e o formato canônico de `evidence`** para servir de template à
> rotina TOTVS de M6.

---

## 1. Arquitetura da rotina

```
┌─────────────────────────────────────────────────────────────────┐
│  python -m orchestrator --routine pilot-smoke [--dry-run]       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │ orchestrator/  │  (M4: boot → registry → dispatch)
                    │   dispatch.py  │  - cria RoutineContext (logger, settings, dry_run)
                    └────────┬───────┘  - intelligence.reset_for_new_execution(settings)
                             │          - chama pilot_smoke.run(ctx)
                             ▼
              ┌──────────────────────────────┐
              │ src/routines/pilot_smoke.py  │   @register("pilot-smoke")
              │                              │   def run(ctx) -> RoutineResult
              └──────────────┬───────────────┘
                             │
        ┌────────────────────┼────────────────────┬──────────────────┐
        ▼                    ▼                    ▼                  ▼
  ┌──────────┐         ┌──────────┐         ┌──────────┐       ┌──────────┐
  │ DESKTOP  │ ──────▶ │  INTEL   │ ──────▶ │   WEB    │ ────▶ │  RESULT  │
  │ (M1)     │         │ (M3)     │         │ (M2)     │       │ (M4)     │
  └──────────┘         └──────────┘         └──────────┘       └──────────┘
   launch_app           validate(data)       fill_form(...)     RoutineResult(
   focus_window         call_llm(prompt)     submit() ou skip      action,
   click templates      decide(...)          em --dry-run          evidence,
   extract_clipboard                                               exit_code_hint)
```

## 2. Sequência detalhada (happy path)

| # | Etapa | Camada | Função invocada | Saída relevante |
|---|---|---|---|---|
| 1 | Boot CLI | M4 | `orchestrator.boot.boot()` | `settings`, `logger` |
| 2 | Lookup rotina | M4 | `registry.get("pilot-smoke")` | `run` callable |
| 3 | Reset LLM | M3 | `intelligence.reset_for_new_execution(settings)` | `CostTracker` zerado |
| 4 | Cria contexto | M4 | `RoutineContext(logger, settings, dry_run)` | `ctx` frozen |
| 5 | Lança app | M1 | `adapter.launch_app("Calculator" \| "calc.exe")` | janela aberta |
| 6 | Foca janela | M1 | `adapter.focus_window("Calculator" \| "Calculadora")` | foco ok |
| 7 | Digita `2 + 3` | M1 | `click_at_template("btn_2.png")`, `_plus`, `_3`, `_equals` | resultado na tela |
| 8 | Extrai resultado | M1 | `extract_via_clipboard()` (após `cmd+a`,`cmd+c` / `ctrl+a`,`ctrl+c`) | `"5"` |
| 9 | Monta dict bruto | rotina | dict literal | `{operation: "2 + 3", result: 5, observation: "..."}` |
| 10 | Valida | M3 | `validate(PilotSmokeData, data)` | `ValidationResult.is_valid=True` |
| 11 | Renderiza prompt | M3 | `prompts.load("pilot-smoke").render(**data)` | `RenderedPrompt` |
| 12 | Chama LLM | M3 | `call_llm(rendered, response_model=PilotSmokeLLM)` | `LLMResult(typed=...)` |
| 13 | Roteia | M3 | `decide(validation, llm)` | `Decision(action=PROCEED_TO_WEB, confidence≥0.7)` |
| 14a | (dry-run) | rotina | early return | `RoutineResult(PROCEED_TO_WEB, {dry_run: True, ...})` |
| 14b | Abre Playwright | M2 | `web.open_session()` | `Page` |
| 15 | Navega | M2 | `page.goto("https://httpbin.org/forms/post")` | DOM carregado |
| 16 | Preenche | M2 | `fill_form("pilot_smoke", data, page=page)` | campos preenchidos |
| 17 | Submete | M2 | `click(selectors["pilot_smoke"]["submit"])` + `wait_for_url` | response page |
| 18 | Captura final URL | M2 | `page.url` | `https://httpbin.org/post` |
| 19 | Fecha browser | M2 | `web.close_session()` | — |
| 20 | Retorna | rotina | `RoutineResult(PROCEED_TO_WEB, evidence)` | `evidence` (ver §4) |
| 21 | Summary | M4 | `summary.emit(...)` | `execution_summary` JSON no log |

## 3. Caminhos alternativos (sad paths)

| Cenário | Onde quebra | Comportamento esperado | Exit code |
|---|---|---|---|
| Calculadora não encontrada / app não abre | passo 5 | `DesktopError` → screenshot em `logs/errors/` | 2 |
| Template não bate em 15s | passo 7 ou 8 | `TemplateNotFoundError` → screenshot | 2 |
| `extract_via_clipboard` retorna não-numérico | passo 9-10 | `ValidationError` (Pydantic) | 1 |
| LLM excede `llm_token_hard_cap` | passo 12 | `TokenBudgetExceededError` | 3 |
| LLM retorna `decision="reject"` | passo 13 | `Decision(action=ABORT_IN_DESKTOP)` → encerra ok | 0 (com action diferente) |
| LLM retorna `confidence < 0.7` | passo 13 | `Decision(action=RAISE_EXCEPTION)` | 4 |
| httpbin offline / timeout | passo 15 | `WebError` (retry exponencial via tenacity primeiro) | 5 |
| Ctrl+C do usuário | qualquer | `KeyboardInterrupt` | 130 |
| Erro inesperado | qualquer | `Exception` genérica → summary com `error_type` | 1 |

Mapeamento de exit codes já implementado em M4 (`dispatch.action_to_exit_code` e
`exception_to_exit_code`) — esta rotina **não** define exit codes próprios.

## 4. Contrato de `evidence` (canônico — será reusado em M6)

```python
evidence: dict[str, Any] = {
    # extração desktop
    "operation": "2 + 3",           # str
    "result": 5,                    # int
    # decisão da inteligência
    "llm_decision": "approve",      # Literal["approve","reject","escalate"]
    "llm_confidence": 0.92,         # float
    "llm_summary": "cálculo de soma simples...",  # str ≤ 200 chars
    # web (ausente em --dry-run)
    "web_final_url": "https://httpbin.org/post",
    "web_status": 200,
    # flag de modo
    "dry_run": False,               # bool
}
```

**Regras:**

- Todas as chaves são **safe**: sem PII, sem segredos, sem prompt cru, sem resposta LLM crua.
- `execution_summary` (M4) registra apenas `evidence_keys = sorted(evidence.keys())` —
  nunca os valores.
- `evidence` é serializável JSON (M4 chama `json.dumps` no logger estruturado se necessário).
- Em `--dry-run`, `evidence` **não** contém `web_final_url`/`web_status` e contém
  `dry_run: True`.

**Por que esse formato:** M6 (TOTVS) reaproveita exatamente a mesma estrutura, trocando
`operation/result` por `cliente_id/pedido_numero/etc`. O `execution_summary` permanece
universal — operador faz `grep '"event":"execution_summary"' logs/*.json | jq` e vê
todas as rotinas com o mesmo shape.

## 5. Artefatos de configuração

### 5.1 Templates (`assets/templates/pilot-smoke/`)

```
assets/templates/pilot-smoke/
├── darwin/                  # se UI macOS divergir significativamente
│   ├── window_titlebar.png  # âncora "Calculadora carregada"
│   ├── btn_2.png
│   ├── btn_3.png
│   ├── btn_plus.png
│   └── btn_equals.png
└── win32/                   # fallback será criado quando houver máquina Windows
    └── (idem)
```

Estratégia de captura (M0): screenshots tirados na Calculadora em **tema claro**, zoom
nativo, resolução real do display. Templates novos vão em `darwin/` por padrão (GA-01)
e migram para `assets/templates/pilot-smoke/` raiz se forem idênticos em ambos SOs.

### 5.2 Schema (`src/intelligence/schemas/pilot_smoke.py`)

```python
from pydantic import BaseModel, Field
from typing import Literal
from intelligence.schemas import register

@register("pilot-smoke")
class PilotSmokeData(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    operation: str = Field(pattern=r"^\d+\s*[+\-*/]\s*\d+$")
    result: int
    observation: str = Field(min_length=1, max_length=500)

@register("pilot-smoke-llm")
class PilotSmokeLLM(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    decision: Literal["approve", "reject", "escalate"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=200)
```

### 5.3 Prompt (`config/prompts/pilot-smoke.md`)

```markdown
---
version: 1
model: ${settings.llm_default_model}   # resolvido em load(); fallback opcional
temperature: 0.0
response_schema: pilot-smoke-llm
---
Você é um classificador de operações de teste.

Operação executada: {operation}
Resultado obtido: {result}
Observação: {observation}

Responda em JSON com os campos `decision`, `confidence` e `summary`:
- decision="approve" se a operação parece legítima e o resultado é plausível;
- decision="reject" se há sinais claros de inconsistência;
- decision="escalate" se ambíguo.
confidence é sua certeza (0-1). summary resume em até 200 chars.
```

### 5.4 Seletores (`config/selectors.json`)

Bloco a adicionar (sem alterar blocos existentes de outras páginas):

```json
{
  "pilot_smoke": {
    "_session_sentinel": "input[name=custname]",
    "custname": "input[name=custname]",
    "custtel": "input[name=custtel]",
    "custemail": "input[name=custemail]",
    "comments": "textarea[name=comments]",
    "submit": "button[type=submit]"
  }
}
```

`_session_sentinel` aponta para um elemento sempre presente na página alvo — se a
verificação de sessão expirada de M2 disparar para httpbin (não deveria, pois não há
login), o sentinel garante que `LoginRequiredError` não suba erroneamente.

## 6. Estrutura do código da rotina

```python
# src/routines/pilot_smoke.py
from orchestrator.registry import register
from orchestrator.types import RoutineContext, RoutineResult
from orchestrator.types import Action

@register("pilot-smoke")
def run(ctx: RoutineContext) -> RoutineResult:
    # 1. Desktop
    raw = _extract_from_calculator(ctx)

    # 2. Validação
    data = validate(PilotSmokeData, raw)  # lança ValidationError se inválido

    # 3. LLM
    prompt = prompts.load("pilot-smoke").render(**data.model_dump())
    llm = call_llm(prompt, response_model=PilotSmokeLLM)

    # 4. Roteamento
    decision = decide(validation_result=data, llm_result=llm)

    if decision.action != Action.PROCEED_TO_WEB:
        return RoutineResult(action=decision.action, evidence=_build_evidence(...))

    # 5. Dry-run gate (decisão M4: contrato, não fiscalização)
    if ctx.dry_run:
        return RoutineResult(
            action=Action.PROCEED_TO_WEB,
            evidence=_build_evidence(..., dry_run=True),
        )

    # 6. Web
    web_result = _submit_to_httpbin(ctx, data, llm)

    return RoutineResult(action=Action.PROCEED_TO_WEB, evidence=_build_evidence(..., web=web_result))
```

Helpers privados (`_extract_from_calculator`, `_submit_to_httpbin`, `_build_evidence`)
ficam no mesmo arquivo — rotina pequena não precisa de submódulo. Quando M6 chegar, se
TOTVS for grande, a rotina pode virar package (`src/routines/totvs/`) sem mudar contrato.

## 7. Testes

### Unitários (rodam sempre, sem Calculadora real)

- `tests/test_routines/test_pilot_smoke_unit.py`
  - `test_run_invokes_pipeline_in_order` — mock de desktop/web/llm; verifica ordem das chamadas.
  - `test_dry_run_skips_web_submit` — `ctx.dry_run=True` → web mock não recebe `submit`.
  - `test_evidence_keys_are_safe` — evidence final não contém chaves prefixadas com `_` nem strings óbvias de PII.
  - `test_low_confidence_raises_exception` — LLM mock retorna `confidence=0.5` → `Action.RAISE_EXCEPTION`.
  - `test_validation_failure_short_circuits` — raw inválido → `ValidationError`, sem chamada LLM.
  - `test_registered_with_correct_name` — `registry.get("pilot-smoke")` resolve para `run`.

### E2E opt-in (`pytest -m e2e` + `RUN_E2E_PILOT_SMOKE=1`)

- `tests/test_routines/test_pilot_smoke_e2e.py::test_full_pipeline_macos`
  - Pula automaticamente em CI e em Windows (até templates win32 existirem).
  - Requer `OPENAI_API_KEY` válida e Calculadora instalada.
  - Asserta exit code 0, `action=PROCEED_TO_WEB`, `tokens_in > 0`, `web_status == 200`.

### Gate de regressão

- Todos os 377+ testes existentes continuam verdes — esta rotina **não** modifica
  M0-M4. Qualquer mudança nesses módulos é tratada como bug separado.

## 8. Decisões de design (registrar em STATE após implementação)

1. **Calculadora como alvo desktop:** disponível em ambos SOs, UI estável, sem custos
   de licenciamento, ótima para validar template matching com elementos pequenos
   (botões).
2. **Observação fixa em vez de extraída do desktop:** Calculadora não tem campo de
   texto livre real. Manter a string fixa preserva o exercício do caminho LLM sem
   forçar uma extração artificial. M6 (TOTVS) terá texto livre genuíno.
3. **Rotina como arquivo único:** ~150 linhas de código previstas. Submódulo seria
   over-engineering. Padrão "rotina pequena = arquivo, rotina grande = package" fica
   estabelecido para M6+.
4. **`--dry-run` early-return antes do Playwright:** consistente com a decisão M4
   (`dry-run` é contrato, não fiscalização). Rotina cumpre o contrato; orquestrador
   não inspeciona.
5. **E2E gateado por env var:** evita rodar em CI por engano (consome quota OpenAI
   real). Localmente, dev exporta `RUN_E2E_PILOT_SMOKE=1` quando quiser smoke.

## 9. O que vira template para M6

- O contrato de `evidence` (§4).
- A sequência de 21 passos (§2) com TOTVS substituindo Calculadora e plataforma
  Consigaz substituindo httpbin.
- A estrutura de schemas dupla (`<rotina>Data` validando extração + `<rotina>LLM`
  validando resposta).
- O padrão de frontmatter do prompt (§5.3).
- A separação unit/E2E com gate por env var (§7).
- A regra "rotina pequena = arquivo, rotina grande = package" (§8.3).
