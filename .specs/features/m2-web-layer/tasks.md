# M2 — Camada Web: Tasks

**Spec**: `.specs/features/m2-web-layer/spec.md`
**Design**: `.specs/features/m2-web-layer/design.md`
**Status**: Draft

> Gate rápido (por módulo): `pytest tests/web/test_<módulo>.py -v`
> Gate completo: `pytest && ruff check src/web/ && mypy src/web/`

---

## Execution Plan

```
Phase 1 (Sequential — Foundation):
  T1 → T2

Phase 2 (Parallel — Config + Session):
  T2 complete, then:
    ├── T3 [P]   selectors.py + config/selectors.json + tests
    └── T4 [P]   session.py + tests

Phase 3 (Sequential — Navigation):
  T3 + T4 complete → T5   navigation.py + tests

Phase 4 (Sequential — Forms):
  T3 + T5 complete → T6   forms.py + tests

Phase 5 (Sequential — Exports + Gate Final):
  T4 + T5 + T6 complete → T7
```

```
T1 → T2 ─┬─ T3 [P] ─┬──────────┐
           │           │          ↓
           └─ T4 [P] ─┼→ T5 ──→ T6 → T7
                       │          ↑
                       └──────────┘
                        (T5 dep: T3+T4)
                        (T6 dep: T3+T5)
```

---

## Task Breakdown

### T1: Scaffold do pacote `web`

**What**: Criar estrutura de diretórios e arquivos `__init__.py` do pacote `web`; registrar `src/web` em `pyproject.toml`; criar `tests/web/__init__.py`; criar diretório `config/` na raiz; adicionar `playwright.*` nos `ignore_missing_imports` do mypy.
**Where**:
- `src/web/__init__.py` (novo, vazio)
- `tests/web/__init__.py` (novo, vazio)
- `config/` (novo diretório — só criar)
- `pyproject.toml` (modificar: adicionar `src/web` em `packages`; adicionar `playwright.*` em `ignore_missing_imports`)
**Depends on**: Nenhuma
**Reuses**: Padrão de T1 do M1 (`src/desktop/__init__.py` + pyproject.toml tweak)
**Requirement**: WEB-01 (scaffold necessário para todos)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `src/web/__init__.py` existe (vazio)
- [ ] `tests/web/__init__.py` existe (vazio)
- [ ] `config/` diretório existe na raiz do projeto
- [ ] `pyproject.toml`: `src/web` adicionado em `[tool.hatch.build.targets.wheel] packages`
- [ ] `pyproject.toml`: `playwright.*` adicionado em `[[tool.mypy.overrides]] ignore_missing_imports`
- [ ] Gate check: `python -c "import web"` retorna exit 0

**Tests**: none
**Gate**: quick (`python -c "import web"`)

**Commit**: `feat(web): scaffold pacote web + config/ dir + mypy override playwright`

---

### T2: `web/exceptions.py` — hierarquia de exceções

**What**: Criar `src/web/exceptions.py` com as 5 exceções customizadas do módulo web; criar `tests/web/test_exceptions.py`.
**Where**:
- `src/web/exceptions.py` (novo)
- `tests/web/test_exceptions.py` (novo)
**Depends on**: T1
**Reuses**: Padrão de `src/desktop/exceptions.py` — atributos tipados, `RuntimeError` como base
**Requirement**: WEB-05, WEB-07, WEB-08, WEB-10, WEB-16, WEB-17

**Exceções a criar**:
```python
class WebError(RuntimeError): ...

class LoginRequiredError(WebError):
    def __init__(self, current_url: str): ...
    # atributos: .current_url

class SelectorNotFoundError(WebError):
    def __init__(self, page: str, key: str): ...
    # atributos: .page, .key

class SelectorLoadError(WebError):
    def __init__(self, path: str, reason: str): ...
    # atributos: .path, .reason

class PageLoadTimeoutError(WebError):
    def __init__(self, url: str, elapsed: float): ...
    # atributos: .url, .elapsed

class TransactionError(WebError):
    def __init__(self, page: str, key: str): ...
    # atributos: .page, .key
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Todas as 5 classes definidas, todas subclasses de `WebError`, que é subclasse de `RuntimeError`
- [ ] Atributos corretos em cada exceção conforme spec
- [ ] Gate check: `pytest tests/web/test_exceptions.py -v` → todos passam
- [ ] Test count: ≥ 10 testes (issubclass, instanciação, atributos de cada exceção)

**Tests**: unit
**Gate**: quick (`pytest tests/web/test_exceptions.py -v`)

**Commit**: `feat(web): exceções WebError, LoginRequiredError, SelectorNotFoundError, PageLoadTimeoutError, TransactionError`

---

### T3: `config/selectors.json` + `web/selectors.py` [P]

**What**: Criar `config/selectors.json` com estrutura de exemplo (página `login` e uma página placeholder); criar `src/web/selectors.py` com `load_selectors()` e `get_selector()`; criar `tests/web/test_selectors.py`.
**Where**:
- `config/selectors.json` (novo)
- `src/web/selectors.py` (novo)
- `tests/web/test_selectors.py` (novo)
**Depends on**: T2
**Reuses**: Padrão de `src/config/settings.py` para `pathlib.Path` e `Path(__file__).parent`; decisão GA-01 (hierarquia página > elemento)
**Requirement**: WEB-06, WEB-07, WEB-08

**`config/selectors.json` a criar**:
```json
{
  "login": {
    "username":           "input[name='username']",
    "password":           "input[name='password']",
    "submit":             "button[type='submit']",
    "_session_sentinel":  "#app-main"
  },
  "_placeholder": {
    "_note": "Adicione páginas reais aqui ao mapear a plataforma Consigaz (M5)"
  }
}
```

**`web/selectors.py`**:
```python
_PROJECT_ROOT = Path(__file__).parent.parent.parent  # src/web/ → projeto raiz
_DEFAULT_PATH = _PROJECT_ROOT / "config" / "selectors.json"

def load_selectors(path: str | Path | None = None) -> dict[str, dict[str, str]]:
    """Carrega JSON; lança FileNotFoundError ou SelectorLoadError."""

def get_selector(
    selectors: dict[str, dict[str, str]], page: str, key: str
) -> str:
    """Retorna seletor; lança SelectorNotFoundError se page ou key não existir."""
```

**Testes com `tmp_path`** do pytest — sem depender de `config/selectors.json` real nos testes unitários.

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `config/selectors.json` existe com estrutura página > elemento
- [ ] `load_selectors()` sem argumento usa `config/selectors.json` relativo à raiz
- [ ] `load_selectors(path)` com path inválido lança `FileNotFoundError`
- [ ] `load_selectors(path)` com JSON malformado lança `SelectorLoadError`
- [ ] `get_selector()` retorna string correta
- [ ] `get_selector()` lança `SelectorNotFoundError` para página/chave ausente
- [ ] Gate check: `pytest tests/web/test_selectors.py -v` → todos passam
- [ ] Test count: ≥ 8 testes (load ok, load FileNotFoundError, load malformed, get ok, get page missing, get key missing, default path, chave _prefixada ignorada-ou-acessível)

**Tests**: unit
**Gate**: quick (`pytest tests/web/test_selectors.py -v`)

**Commit**: `feat(web): config/selectors.json + selectors.py (load_selectors, get_selector)`

---

### T4: `web/session.py` — sessão persistida [P]

**What**: Criar `src/web/session.py` com `open_browser()` e `close_browser()`; lazy import de playwright; perfil cross-platform; detecção de sessão expirada; criar `tests/web/test_session.py`.
**Where**:
- `src/web/session.py` (novo)
- `tests/web/test_session.py` (novo)
**Depends on**: T2
**Reuses**: `src/config/settings.py` para `Settings`; padrão de lazy import de `src/desktop/platform/win.py`; exceções de T2
**Requirement**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-18, WEB-19, WEB-20

**Assinaturas**:
```python
def open_browser(
    settings: Settings,
    selectors: dict[str, dict[str, str]] | None = None,
) -> "Page":
    """
    Abre chromium com perfil persistido.
    Detecta sessão expirada via URL + sentinel (GA-03).
    Retorna Page pronta para uso.
    """

def close_browser() -> None:
    """Fecha contexto; no-op se não aberto."""

def _profile_path() -> Path:
    """Retorna Path cross-platform para ~/.consigaz-robo/playwright-profile/."""
```

**Lazy import**:
```python
def open_browser(...):
    from playwright.sync_api import sync_playwright, Page  # lazy
    ...
```

**Mock de playwright nos testes**:
```python
with patch("web.session.sync_playwright") as mock_pw:
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_page.url = "https://app.consigaz.com.br/dashboard"
    mock_context.new_page.return_value = mock_page
    mock_pw.return_value.__enter__.return_value.chromium\
        .launch_persistent_context.return_value = mock_context
    ...
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `import web.session` não lança ImportError mesmo sem playwright instalado (lazy import)
- [ ] `_profile_path()` retorna `Path.home() / ".consigaz-robo" / "playwright-profile"`
- [ ] `open_browser()` chama `launch_persistent_context(user_data_dir=profile_path, headless=settings.web_headless, ...)`
- [ ] `open_browser()` aplica `user_agent`, `viewport`, `locale` de settings
- [ ] `open_browser()` lança `LoginRequiredError` se URL bate padrão de login
- [ ] `close_browser()` é no-op quando context é None
- [ ] Gate check: `pytest tests/web/test_session.py -v` → todos passam
- [ ] Test count: ≥ 8 testes (open ok, profile path, headless flag, LoginRequiredError por URL, close com context, close sem context, cabeçalhos aplicados, perfil criado se não existe)

**Tests**: unit
**Gate**: quick (`pytest tests/web/test_session.py -v`)

**Commit**: `feat(web): session.py — open/close browser com perfil persistido cross-platform`

---

### T5: `web/navigation.py` — navegação e espera

**What**: Criar `src/web/navigation.py` com `navigate_to()` e `wait_for_selector()`; retry exponencial em `navigate_to` via tenacity; criar `tests/web/test_navigation.py`.
**Where**:
- `src/web/navigation.py` (novo)
- `tests/web/test_navigation.py` (novo)
**Depends on**: T3, T4
**Reuses**: `tenacity` (já em deps); exceções de T2; `get_selector()` de T3
**Requirement**: WEB-09, WEB-10, WEB-11

**Assinaturas**:
```python
def navigate_to(
    page: "Page",
    url: str,
    timeout: float = 30.0,
) -> None:
    """
    Navega para URL, aguarda 'networkidle'.
    Retry exponencial (≤3 tentativas) em PageLoadTimeoutError.
    """

def wait_for_selector(
    page: "Page",
    selectors: dict[str, dict[str, str]],
    page_name: str,
    key: str,
    timeout: float = 15.0,
) -> "Locator":
    """Resolve seletor via get_selector(), aguarda visibilidade."""
```

**Retry**:
```python
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(PageLoadTimeoutError),
)
def navigate_to(...) -> None: ...
```

**Type annotations com `TYPE_CHECKING`**:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from playwright.sync_api import Page, Locator
```
Isso evita ImportError em runtime quando playwright não está instalado.

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `navigate_to` chama `page.goto(url, wait_until="networkidle", timeout=timeout*1000)`
- [ ] Playwright `TimeoutError` é capturada e relançada como `PageLoadTimeoutError`
- [ ] `navigate_to` tem retry com `wait_exponential` via tenacity
- [ ] `wait_for_selector` resolve seletor via `get_selector()` e chama `page.locator(sel).wait_for(timeout=timeout*1000)`
- [ ] Playwright `TimeoutError` em `wait_for_selector` é relançada como `SelectorNotFoundError`
- [ ] Gate check: `pytest tests/web/test_navigation.py -v` → todos passam
- [ ] Test count: ≥ 8 testes (navigate ok, navigate timeout→PageLoadTimeoutError, navigate retry, wait_for ok, wait_for timeout→SelectorNotFoundError, wait_for page missing, wait_for key missing, retry esgotado→exceção final)

**Tests**: unit
**Gate**: quick (`pytest tests/web/test_navigation.py -v`)

**Commit**: `feat(web): navigation.py — navigate_to com retry + wait_for_selector`

---

### T6: `web/forms.py` — preenchimento e captura

**What**: Criar `src/web/forms.py` com `fill_form()`, `handle_modal()` e `capture_transaction_id()`; criar `tests/web/test_forms.py`.
**Where**:
- `src/web/forms.py` (novo)
- `tests/web/test_forms.py` (novo)
**Depends on**: T3, T5
**Reuses**: `get_selector()` de T3; `wait_for_selector()` de T5; exceções de T2
**Requirement**: WEB-12, WEB-13, WEB-14, WEB-15, WEB-16

**Assinaturas**:
```python
def fill_form(
    page: "Page",
    selectors: dict[str, dict[str, str]],
    page_name: str,
    data: dict[str, str | None],
) -> None:
    """
    Para cada chave em data (que não começa com '_'):
    - Ignora se valor é None
    - Obtém seletor via get_selector(selectors, page_name, key)
    - Se tag == SELECT: usa select_option(value=v)
    - Senão: fill("") para limpar, depois fill(v)
    """

def handle_modal(page: "Page") -> bool:
    """
    Procura botões de fechar por aria-label, texto ('OK', 'Fechar', 'Entendi').
    Clica no primeiro encontrado; retorna True se fechou, False se não havia modal.
    """

def capture_transaction_id(
    page: "Page",
    selectors: dict[str, dict[str, str]],
    page_name: str,
    key: str,
) -> str:
    """
    Extrai inner_text() do seletor.
    Lança TransactionError se vazio ou em branco.
    """
```

**Detecção de `<select>` no fill_form**:
```python
locator = page.locator(selector)
tag = locator.evaluate("el => el.tagName.toLowerCase()")
if tag == "select":
    locator.select_option(value=value)
else:
    locator.fill("")
    locator.fill(value)
```

**handle_modal — seletores tentados em ordem**:
1. `[aria-label*='fechar' i]`
2. `[aria-label*='close' i]`
3. `button:has-text('OK')`
4. `button:has-text('Fechar')`
5. `button:has-text('Entendi')`

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `fill_form` ignora chaves prefixadas com `_`
- [ ] `fill_form` ignora campos com valor `None` (sem chamar playwright)
- [ ] `fill_form` usa `select_option` para `<select>`
- [ ] `fill_form` lança `SelectorNotFoundError` para chave ausente (antes de interagir)
- [ ] `handle_modal` retorna `False` se nenhum botão encontrado (sem exceção)
- [ ] `capture_transaction_id` retorna string não vazia
- [ ] `capture_transaction_id` lança `TransactionError` se inner_text vazio/branco
- [ ] Gate check: `pytest tests/web/test_forms.py -v` → todos passam
- [ ] Test count: ≥ 12 testes (fill ok, fill None skip, fill select, fill chave ausente, fill _ skip, modal fechado, modal ausente, capture ok, capture vazio→TransactionError, fill falha playwright→WebError, fill data vazia, capture whitespace→TransactionError)

**Tests**: unit
**Gate**: quick (`pytest tests/web/test_forms.py -v`)

**Commit**: `feat(web): forms.py — fill_form, handle_modal, capture_transaction_id`

---

### T7: Exports públicos + gate completo do M2

**What**: Atualizar `src/web/__init__.py` com exports públicos; adicionar `src/web` a `settings.py` se necessário; rodar gate completo (pytest + ruff + mypy) e corrigir qualquer falha.
**Where**:
- `src/web/__init__.py` (modificar)
- `src/config/settings.py` (modificar: adicionar campos `web_*` de design.md)
**Depends on**: T4, T5, T6
**Reuses**: Padrão de `src/desktop/__init__.py` (T8 do M1)
**Requirement**: todos (verificação final)

**Exports esperados em `web/__init__.py`**:
```python
from web.exceptions import (
    WebError,
    LoginRequiredError,
    SelectorNotFoundError,
    SelectorLoadError,
    PageLoadTimeoutError,
    TransactionError,
)
from web.selectors import load_selectors, get_selector
from web.session import open_browser, close_browser
from web.navigation import navigate_to, wait_for_selector
from web.forms import fill_form, handle_modal, capture_transaction_id
```

**Campos a adicionar em `settings.py`**:
```python
web_headless: bool = False
web_login_url_patterns: list[str] = ["/login", "/auth", "/signin", "/entrar"]
web_default_timeout: float = 15.0
web_navigate_timeout: float = 30.0
web_user_agent: str = "Mozilla/5.0 ..."
web_viewport_width: int = 1280
web_viewport_height: int = 800
web_locale: str = "pt-BR"
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `from web import open_browser, fill_form, load_selectors` funciona
- [ ] `src/config/settings.py` contém todos os campos `web_*`
- [ ] `pytest tests/web/ -v` → todos passam (≥ 54 testes: soma dos gates anteriores)
- [ ] `pytest` (suite completa) → todos os testes anteriores continuam passando + novos de M2
- [ ] `ruff check src/web/` → zero erros
- [ ] `mypy src/web/` → zero erros (strict mode)
- [ ] Nenhum seletor CSS/XPath hardcoded em nenhum arquivo Python de `src/web/`

**Tests**: integration (smoke)
**Gate**: full (`pytest && ruff check src/web/ && mypy src/web/`)

**Commit**: `feat(web): exports públicos M2 + settings web_* + gate completo verde`

---

## Parallel Execution Map

```
Phase 1 (Sequential — Foundation):
  T1 → T2

Phase 2 (Parallel — após T2):
  T2 complete:
    ├── T3 [P]   selectors.py + config/selectors.json
    └── T4 [P]   session.py

Phase 3 (Sequential — após T3+T4):
  T3+T4 complete → T5   navigation.py

Phase 4 (Sequential — após T3+T5):
  T3+T5 complete → T6   forms.py

Phase 5 (Sequential — após T4+T5+T6):
  T4+T5+T6 complete → T7   exports + gate final
```

**Constraint T3 vs T4**: Paralelos — T3 lida com JSON/config; T4 lida com playwright/session. Nenhum depende do outro; apenas ambos dependem de T2 (exceções).

**Constraint T5**: Depende de T3 (precisa de `get_selector()`) e T4 (precisa de `Page` mockável).

**Constraint T6**: Depende de T3 (seletores) e T5 (`wait_for_selector` é usado internamente).

---

## Task Granularity Check

| Task | Escopo | Status |
|---|---|---|
| T1: Scaffold | 2 `__init__.py` + `config/` dir + pyproject.toml tweak | ✅ Granular |
| T2: exceptions.py | 1 arquivo, 5 classes | ✅ Granular |
| T3: selectors.py + JSON | 2 arquivos, 2 funções | ✅ Granular |
| T4: session.py | 1 arquivo, 2 funções + _profile_path | ✅ Granular |
| T5: navigation.py | 1 arquivo, 2 funções | ✅ Granular |
| T6: forms.py | 1 arquivo, 3 funções coesas | ✅ OK (formulário é unidade coesa) |
| T7: exports + gate | 2 arquivos modificados + verificação | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagrama mostra | Status |
|---|---|---|---|
| T1 | Nenhuma | Início | ✅ |
| T2 | T1 | T1 → T2 | ✅ |
| T3 [P] | T2 | T2 → T3 | ✅ |
| T4 [P] | T2 | T2 → T4 | ✅ |
| T5 | T3, T4 | T3+T4 → T5 | ✅ |
| T6 | T3, T5 | T3+T5 → T6 | ✅ |
| T7 | T4, T5, T6 | T4+T5+T6 → T7 | ✅ |

---

## Test Co-location Validation

| Task | Camada criada | Tipo requerido | Task diz | Status |
|---|---|---|---|---|
| T1 | Scaffold (sem lógica) | none | none | ✅ |
| T2 | exceptions.py | unit | unit | ✅ |
| T3 | selectors.py + JSON | unit | unit | ✅ |
| T4 | session.py (playwright) | unit com mocks | unit | ✅ |
| T5 | navigation.py | unit com mocks | unit | ✅ |
| T6 | forms.py | unit com mocks | unit | ✅ |
| T7 | __init__.py + settings tweak | integration smoke | integration | ✅ |

---

## Requirement Coverage

| Requirement | Task | Status |
|---|---|---|
| WEB-01 | T4 | Pending |
| WEB-02 | T4 | Pending |
| WEB-03 | T4 | Pending |
| WEB-04 | T4 | Pending |
| WEB-05 | T2, T4 | Pending |
| WEB-06 | T3 | Pending |
| WEB-07 | T2, T3 | Pending |
| WEB-08 | T2, T3 | Pending |
| WEB-09 | T5 | Pending |
| WEB-10 | T2, T5 | Pending |
| WEB-11 | T5 | Pending |
| WEB-12 | T6 | Pending |
| WEB-13 | T6 | Pending |
| WEB-14 | T6 | Pending |
| WEB-15 | T6 | Pending |
| WEB-16 | T2, T6 | Pending |
| WEB-17 | T2 | Pending |
| WEB-18 | T4 | Pending |
| WEB-19 | T4, T7 | Pending |
| WEB-20 | T4 | Pending |

**Coverage:** 20/20 mapeados ✅
