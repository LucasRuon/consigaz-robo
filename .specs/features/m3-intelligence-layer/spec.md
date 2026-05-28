# M3 — Camada de Inteligência

## Problem Statement

Hoje o robô tem capacidade de extrair dados do app desktop (M1) e injetá-los em formulários web (M2), mas não há nenhuma lógica entre essas duas pontas. Os dados extraídos podem estar incompletos, inconsistentes ou conter texto livre que precisa ser classificado antes de virar input estruturado para a web. Sem M3, qualquer rotina vai (a) confiar cegamente no que veio do desktop, ou (b) precisar embutir regras de negócio dentro dos módulos de UI — violando a separação arquitetural do PRD.

M3 entrega três responsabilidades isoladas:

1. **Validação determinística (Pydantic + helpers Pandas)** — schema-first, roda ANTES de qualquer chamada cara à LLM. Falha rápido em dados malformados.
2. **Cliente OpenAI** — wrapper com retry exponencial, prompts versionados em arquivos `.md` com frontmatter, resposta tipada (Pydantic) e guard rail de custo (cap em tokens + warning em USD).
3. **Roteador de decisão** — função pura que recebe resultado da validação + resultado da LLM e retorna uma `Decision` (action + reason + evidence + confidence), sem side-effects.

O orquestrador (M4) consome essas três peças sequencialmente: dados extraídos → validar → (se válido) chamar LLM → decidir → repassar para a web (ou abortar).

## Goals

- [ ] `intelligence/validation.py` com schemas Pydantic + helpers Pandas para análises agregadas (ranges, comparações numéricas)
- [ ] `intelligence/llm.py` com cliente OpenAI: retry exponencial (`tenacity`), resposta tipada via Pydantic, cap em tokens hard + warning em USD
- [ ] `intelligence/prompts.py` carrega arquivos `.md` de `config/prompts/` com frontmatter YAML (model, temperature, response_schema, version)
- [ ] `intelligence/router.py` com função pura `decide(validation, llm_result) → Decision` cobrindo aprovado / reprovado / exceção / baixa-confiança
- [ ] 100% dos caminhos de código cobertos por testes unitários sem chamar OpenAI real (mocks via `respx` ou `unittest.mock`)
- [ ] Zero segredo logado; zero prompt ou resposta com PII gravado sem sanitização

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rotinas reais de validação/classificação | M5 — depende de domínio Consigaz |
| Abstração multi-LLM (Anthropic, locais) | Decisão STATE 2026-05-28: YAGNI v1 |
| Modo "atendido" (humano confirma baixa confiança) | Deferred Idea — campo `confidence` fica pronto, mas decisor v1 trata `< threshold` como `RAISE_EXCEPTION` |
| Fine-tuning / embeddings / RAG | Não está no PRD |
| Cache persistente de respostas LLM | Não há requisito de idempotência; reavaliar em M5 |
| Streaming de resposta | Robô é batch — resposta completa basta |
| Pricing dinâmico via API OpenAI | Tabela de preços vive em config; atualização manual |

---

## User Stories

### P1: Validação Estruturada ⭐ MVP

**User Story**: Como orquestrador, quero validar um dict de dados extraídos contra um schema Pydantic antes de chamar a LLM, para falhar rápido em dados malformados e economizar tokens.

**Why P1**: Validação é a primeira porta — sem ela, dados ruins chegam à LLM e geram resposta inútil + custo.

**Acceptance Criteria**:

1. WHEN `validate(data, schema)` é chamado com `data: dict` e `schema: type[BaseModel]` THEN SHALL retornar `ValidationResult(is_valid=True, model=<instance>, errors=[], warnings=[])`
2. WHEN `data` viola schema THEN SHALL retornar `ValidationResult(is_valid=False, model=None, errors=[<lista de mensagens>], warnings=[])` SEM lançar exceção
3. WHEN schema declara campo obrigatório e `data` o omite THEN `errors` SHALL conter `"<field>: campo obrigatório ausente"`
4. WHEN schema declara `Annotated[Decimal, Field(ge=0)]` e valor é negativo THEN `errors` SHALL conter o campo + razão (`"valor menor que 0"`)
5. WHEN `validate_range(value, lo, hi, field_name)` é chamado com valor fora do range THEN SHALL retornar string de erro descritiva; in-range retorna `None`
6. WHEN `compare_against_history(value, series, threshold_std=2)` é chamado com Pandas Series THEN SHALL retornar `True` se valor está dentro de `threshold_std` desvios padrão da média; `False` caso contrário
7. WHEN schema Pydantic é criado com `model_config = {"extra": "forbid"}` THEN dados com chaves extras SHALL aparecer em `errors`
8. WHEN `validate()` é chamado e schema lança exceção não-`ValidationError` (ex: bug no validador customizado) THEN SHALL relançar como `ValidationCodeError` (separa erro de dados de erro de código)

**Independent Test**: `pytest tests/intelligence/test_validation.py` — schemas de exemplo definidos no próprio teste; sem dependência externa.

---

### P1: Cliente OpenAI com Retry e Resposta Tipada ⭐ MVP

**User Story**: Como camada de inteligência, quero chamar a OpenAI com retry exponencial e receber resposta parseada num modelo Pydantic, para que falhas transitórias não derrubem a rotina e a resposta seja typesafe downstream.

**Why P1**: Sem retry, falha de rede mata a execução. Sem tipagem, o roteador trabalha com `dict` opaco.

**Acceptance Criteria**:

1. WHEN `call_llm(prompt_name, params, response_model)` é chamado THEN SHALL carregar prompt via `prompts.load(prompt_name)`, renderizar com `params`, chamar OpenAI, parsear resposta em `response_model` e retornar `LLMResult(model_instance, usage, cost_usd_estimate, latency_ms)`
2. WHEN OpenAI retorna 429 ou 5xx THEN SHALL retentar com `tenacity` (exponencial: 1s, 2s, 4s, 8s; máx 4 tentativas)
3. WHEN todas as tentativas falham THEN SHALL lançar `LLMUnavailableError` com última exceção encaixada
4. WHEN OpenAI retorna 4xx (≠429) THEN SHALL lançar `LLMRequestError` SEM retry
5. WHEN resposta não bate com `response_model` (JSON inválido ou campos faltando) THEN SHALL retentar até 2x com mesma chamada (modelo às vezes erra schema); se persistir, lançar `LLMResponseSchemaError`
6. WHEN `tokens_used + tokens_pending > settings.llm_token_hard_cap` THEN SHALL lançar `TokenBudgetExceededError` ANTES de fazer a chamada
7. WHEN custo acumulado estimado em USD ultrapassa `settings.llm_cost_warning_usd` THEN SHALL emitir log estruturado nível WARNING com campos `acumulado_usd`, `cap_usd`; NÃO bloqueia
8. WHEN `call_llm()` retorna THEN o log estruturado SHALL conter `prompt_name`, `prompt_version`, `model`, `tokens_in`, `tokens_out`, `cost_usd`, `latency_ms` — NUNCA o conteúdo do prompt nem da resposta crua (sanitização)
9. WHEN cliente é instanciado sem `OPENAI_API_KEY` (env nem keyring) THEN SHALL lançar `LLMConfigError` na primeira chamada (lazy)
10. WHEN response_model é `None` THEN SHALL retornar `LLMResult.model_instance = <str da resposta crua>` (modo texto livre)

**Independent Test**: `pytest tests/intelligence/test_llm.py` — usa `respx` ou `monkeypatch` em `openai.OpenAI` para simular respostas; nunca toca a API real.

---

### P1: Prompts Versionados em Markdown ⭐ MVP

**User Story**: Como mantenedor, quero editar prompts em arquivos `.md` versionados com frontmatter (model, temperature, response_schema, version), para evoluir prompts sem mexer em código Python.

**Why P1**: Requisito explícito do roadmap M3 ("Prompts versionados em `config/prompts/` — não no código").

**Acceptance Criteria**:

1. WHEN `prompts.load(name)` é chamado THEN SHALL ler `config/prompts/<name>.md`, parsear frontmatter YAML (delimitado por `---`) e retornar `Prompt(template: str, model: str, temperature: float, response_schema: str | None, version: str)`
2. WHEN arquivo não existe THEN SHALL lançar `PromptNotFoundError(name=name, path=path)`
3. WHEN frontmatter está malformado THEN SHALL lançar `PromptMetadataError` com a linha do YAML problemática
4. WHEN frontmatter omite `model` THEN SHALL usar `settings.llm_default_model`
5. WHEN frontmatter omite `temperature` THEN SHALL usar `settings.llm_default_temperature`
6. WHEN frontmatter omite `version` THEN SHALL lançar `PromptMetadataError` (versão é obrigatória para auditoria)
7. WHEN `prompt.render(params)` é chamado THEN SHALL fazer substituição de placeholders `{var}` no template; placeholder ausente em `params` lança `PromptRenderError(missing=[...])`
8. WHEN `prompt.render()` recebe `params` com chave extra THEN SHALL ignorar (não erro — permite reutilizar dict do orquestrador)

**Independent Test**: `pytest tests/intelligence/test_prompts.py` — usa `tmp_path` para arquivos de prompt em memória.

---

### P1: Roteador de Decisão (função pura) ⭐ MVP

**User Story**: Como orquestrador, quero passar `ValidationResult` + `LLMResult | None` para uma função pura `decide()` e receber uma `Decision` estruturada, para que a lógica de roteamento seja testável determinísticamente e não vaze para módulos de UI.

**Why P1**: É o ponto onde "vai pra web ou aborta no desktop" é decidido — precisa ser bombproof e auditável.

**Acceptance Criteria**:

1. WHEN `decide(validation, llm_result=None)` é chamado e `validation.is_valid == False` THEN SHALL retornar `Decision(action=Action.ABORT_IN_DESKTOP, reason="dados inválidos", evidence={"errors": validation.errors}, confidence=1.0)`
2. WHEN `validation.is_valid == True` e `llm_result is None` THEN SHALL retornar `Decision(action=Action.PROCEED_TO_WEB, reason="validação ok, sem análise LLM necessária", evidence={"model": validation.model.model_dump()}, confidence=1.0)`
3. WHEN `llm_result.model_instance` expõe atributo `decision` (string `"approve"`, `"reject"`, `"escalate"`) THEN SHALL mapear para `Action.PROCEED_TO_WEB`, `Action.ABORT_IN_DESKTOP`, `Action.RAISE_EXCEPTION` respectivamente
4. WHEN `llm_result.model_instance` expõe atributo `confidence: float` < `settings.llm_min_confidence` (default 0.7) THEN SHALL forçar `Action.RAISE_EXCEPTION` independente do `decision` da LLM, com `reason` indicando baixa confiança
5. WHEN `llm_result.model_instance` não expõe `decision` THEN SHALL lançar `RouterContractError` (modelo da resposta não satisfaz o contrato esperado pelo roteador)
6. WHEN `decide()` é chamado THEN SHALL ser função pura — sem I/O, sem logging, sem mutação de argumentos
7. WHEN `Decision` é serializado via `model_dump()` THEN SHALL produzir JSON com chaves `action`, `reason`, `evidence`, `confidence` — consumível por logger estruturado e pelo orquestrador

**Independent Test**: `pytest tests/intelligence/test_router.py` — table-driven: matriz de (validation, llm_result) → Decision esperada.

---

## Edge Cases

- WHEN `validate(data, schema)` recebe `data=None` THEN SHALL retornar `ValidationResult(is_valid=False, errors=["payload vazio"])` sem lançar
- WHEN `call_llm` é interrompido (KeyboardInterrupt) durante retry THEN SHALL propagar imediatamente (sem mais retries)
- WHEN `prompts.load("path/com/slash")` é chamado THEN SHALL rejeitar (`PromptNameError`) — apenas nomes simples, sem traversal
- WHEN `Decision.evidence` contém `Decimal`, `datetime` ou outro tipo não-JSON nativo THEN `model_dump(mode="json")` SHALL serializar corretamente (usar Pydantic v2 mode="json")
- WHEN dois chamadores compartilham a mesma instância de cliente OpenAI E ambos acumulam tokens THEN o contador SHALL ser thread-safe? **Não na v1** — orquestrador é single-thread. Documentar a premissa.
- WHEN frontmatter YAML do prompt declara `response_schema: "OrderClassification"` mas a classe não existe no registry THEN SHALL lançar `PromptMetadataError` no `load`, não no `call_llm` (falha cedo)
- WHEN custo acumulado já passou o warning e nova chamada vai estourar o hard cap em tokens THEN ordem das verificações é: hard cap PRIMEIRO (bloqueia), warning DEPOIS (não bloqueia)

---

## Gray Areas

### GA-01: Forma do schema de validação (Pydantic puro vs. híbrido com Pandas)

**Decisão tomada (2026-05-28)**: **Híbrido — Pydantic para schema do registro + helpers Pandas para análises agregadas**. Dados extraídos por execução são tipicamente um único registro estruturado (dict), e Pydantic v2 dá tipagem forte, mensagens de erro nativas e integração natural com `pydantic-settings`. Helpers Pandas (`validate_range`, `compare_against_history`) ficam separados para casos onde uma série histórica é necessária (ex: detectar valor anômalo comparando com últimas N execuções). Esses helpers são **opcionais por rotina** — não obrigatórios no caminho crítico.

**Implicação**: Cada rotina (M5) define seu schema como subclasse de `BaseModel` em `intelligence/schemas/<rotina>.py`. Helpers Pandas vivem em `intelligence/analysis.py`. Quem precisa, importa.

---

### GA-02: Tipo da `Action` retornada pelo roteador

**Decisão tomada (2026-05-28)**: **Dataclass `Decision` com action + reason + evidence + confidence**. Mais que enum simples — carrega contexto estruturado para o orquestrador logar/auditar. Inclui `confidence: float` (0-1) já na v1 mesmo que o modo "atendido" seja Deferred Idea, porque é barato adicionar agora e custoso refatorar depois. Decisor v1 trata `confidence < settings.llm_min_confidence` como `RAISE_EXCEPTION` (não escala para humano ainda).

```python
class Action(str, Enum):
    PROCEED_TO_WEB = "proceed_to_web"
    ABORT_IN_DESKTOP = "abort_in_desktop"
    RAISE_EXCEPTION = "raise_exception"

class Decision(BaseModel):
    action: Action
    reason: str
    evidence: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
```

**Implicação**: Logger estruturado registra `decision.model_dump(mode="json")` em cada execução — rastreabilidade total da decisão sem inventar campos no log.

---

### GA-03: Guard rail de custo da LLM (tokens vs. USD vs. ambos)

**Decisão tomada (2026-05-28)**: **Hard cap em tokens + warning em USD**. Tokens são o limite executável (independem de tabela de preços e evitam mudança de comportamento se a OpenAI ajustar pricing). USD é informação para auditoria/dashboards — só warning no log, não bloqueia. Tabela de preços vive em `config.py` (constante editável manualmente).

**Settings novos**:
- `llm_token_hard_cap: int = 100_000` (por execução)
- `llm_cost_warning_usd: float = 1.00` (por execução)
- `llm_model_prices: dict[str, tuple[float, float]]` — (preço/1k input tokens, preço/1k output tokens) por modelo

**Implicação**: Mudança de preço da OpenAI exige update em `config.py`. Hard cap é defensivo — se prompts crescerem muito, a falha é previsível (token count) e não-financeira (cost).

---

### GA-04: Formato dos prompts em `config/prompts/`

**Decisão tomada (2026-05-28)**: **Arquivos `.md` com frontmatter YAML**. Um `.md` por prompt (`config/prompts/<nome>.md`). Frontmatter delimitado por `---` com campos `version` (obrigatório), `model` (opcional, default `settings.llm_default_model`), `temperature` (opcional, default `settings.llm_default_temperature`), `response_schema` (opcional, nome de classe Pydantic registrada). Corpo do `.md` é o template com placeholders `{var}`.

**Exemplo**:

```markdown
---
version: 1.0.0
model: gpt-4o-mini
temperature: 0.0
response_schema: ObservationClassification
---
Você é um classificador de observações de campo da Consigaz.

Classifique a observação abaixo em uma das categorias: [vazamento, leitura, manutencao, outros].

Observação: {observacao}

Responda em JSON: {{"decision": "...", "category": "...", "confidence": 0.0-1.0}}
```

**Implicação**: Mantenedores editam prompts sem tocar em Python. Diffs de prompt ficam legíveis em PR. Versão obrigatória força bump consciente. Registry de schemas (`response_schema` → classe Pydantic) vive em `intelligence/schemas/__init__.py`.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|---|---|---|---|
| INT-01 | P1: `validate(data, schema) → ValidationResult` | Design | Pending |
| INT-02 | P1: Erros tipados em `ValidationResult.errors` (campo + razão) | Design | Pending |
| INT-03 | P1: `extra="forbid"` em schemas detecta chaves extras | Design | Pending |
| INT-04 | P1: `validate_range(value, lo, hi)` helper | Design | Pending |
| INT-05 | P1: `compare_against_history(value, series, threshold_std)` helper | Design | Pending |
| INT-06 | P1: `ValidationCodeError` separa bug de validador de dado inválido | Design | Pending |
| INT-07 | P1: `call_llm(prompt_name, params, response_model) → LLMResult` | Design | Pending |
| INT-08 | P1: Retry exponencial em 429/5xx (tenacity, 4 tentativas) | Design | Pending |
| INT-09 | P1: `LLMUnavailableError` após esgotar retries | Design | Pending |
| INT-10 | P1: `LLMRequestError` em 4xx (≠429) sem retry | Design | Pending |
| INT-11 | P1: Retry em resposta com schema inválido (até 2x) | Design | Pending |
| INT-12 | P1: `LLMResponseSchemaError` se schema persistir inválido | Design | Pending |
| INT-13 | P1: Hard cap em tokens por execução (`TokenBudgetExceededError`) | Design | Pending |
| INT-14 | P1: Warning em USD acima de threshold (log, não bloqueia) | Design | Pending |
| INT-15 | P1: Log estruturado sem prompt/resposta crua (sanitização) | Design | Pending |
| INT-16 | P1: `LLMConfigError` se `OPENAI_API_KEY` ausente | Design | Pending |
| INT-17 | P1: Modo texto livre (`response_model=None`) retorna str | Design | Pending |
| INT-18 | P1: `prompts.load(name) → Prompt` com frontmatter YAML | Design | Pending |
| INT-19 | P1: `PromptNotFoundError` / `PromptMetadataError` / `PromptNameError` | Design | Pending |
| INT-20 | P1: `version` obrigatória no frontmatter | Design | Pending |
| INT-21 | P1: `prompt.render(params)` substitui placeholders `{var}` | Design | Pending |
| INT-22 | P1: `PromptRenderError` lista placeholders ausentes | Design | Pending |
| INT-23 | P1: Rejeitar nomes de prompt com `/` (traversal) | Design | Pending |
| INT-24 | P1: `decide(validation, llm_result) → Decision` (função pura) | Design | Pending |
| INT-25 | P1: `validation.is_valid=False` → `ABORT_IN_DESKTOP` | Design | Pending |
| INT-26 | P1: `validation` ok + `llm_result=None` → `PROCEED_TO_WEB` | Design | Pending |
| INT-27 | P1: Mapeamento `approve/reject/escalate` → Action | Design | Pending |
| INT-28 | P1: `confidence < settings.llm_min_confidence` força `RAISE_EXCEPTION` | Design | Pending |
| INT-29 | P1: `RouterContractError` se LLM result não expõe `decision` | Design | Pending |
| INT-30 | P1: `Decision.model_dump(mode="json")` serializa Decimal/datetime | Design | Pending |

**Coverage:** 30 total, 0 mapeados a tasks, 30 unmapped ⚠️

---

## Success Criteria

- [ ] `pytest tests/intelligence/` passa 100% sem chamar OpenAI real (mocks via `respx` ou `monkeypatch`)
- [ ] `mypy src/intelligence/` retorna zero erros (strict mode)
- [ ] `ruff check src/intelligence/` limpo
- [ ] Nenhum prompt embutido em código Python — todos em `config/prompts/<nome>.md`
- [ ] Nenhum segredo (`OPENAI_API_KEY`) aparece em log ou screenshot
- [ ] Prompt/resposta crua nunca aparece em log estruturado (sanitização verificada por teste)
- [ ] `decide()` é função pura — verificado por teste que executa 100x com mesmo input e compara resultados
- [ ] Guard rail de tokens dispara `TokenBudgetExceededError` ANTES da chamada (verificado por teste)
- [ ] Warning de USD aparece no log quando custo acumulado passa threshold (verificado por teste)
