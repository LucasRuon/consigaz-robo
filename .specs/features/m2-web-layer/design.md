# M2 — Camada Web: Design

**Spec**: `.specs/features/m2-web-layer/spec.md`

---

## Visão Geral

O módulo `web/` encapsula toda interação com o navegador via Playwright (sync API). A separação de responsabilidades segue o mesmo padrão do `desktop/`: exceções → dados/config → session → navegação → formulários → exports.

```
src/web/
├── __init__.py          # exports públicos
├── exceptions.py        # hierarquia de exceções do módulo
├── selectors.py         # loader + accessor de config/selectors.json
├── session.py           # open/close browser com perfil persistido
├── navigation.py        # navigate_to, wait_for_selector
└── forms.py             # fill_form, handle_modal, capture_transaction_id

config/
└── selectors.json       # única fonte de verdade para seletores DOM

tests/web/
├── __init__.py
├── test_exceptions.py
├── test_selectors.py
├── test_session.py
├── test_navigation.py
└── test_forms.py
```

---

## Decisões Arquiteturais

### Playwright Sync API (não Async)

O orquestrador v1 é síncrono (não usa `asyncio`). Usar `playwright.sync_api` mantém consistência e evita conversão de toda a pilha de chamada para async. Revisitar em M4 se o agendador exigir concorrência.

### Sync API + Context Manager

```python
from playwright.sync_api import sync_playwright, BrowserContext

_context: BrowserContext | None = None

def open_browser(settings: Settings) -> BrowserContext:
    global _context
    ...

def close_browser() -> None:
    global _context
    if _context:
        _context.close()
        _context = None
```

Estado do browser fica em variável de módulo. Rotinas chamam `open_browser()` no início e `close_browser()` no `finally` do orquestrador. Sem singleton de classe — mantém interface funcional como o restante do projeto.

### Perfil Persistente Cross-Platform

```python
from pathlib import Path
import sys

def _profile_path() -> Path:
    if sys.platform == "win32":
        base = Path.home()  # %USERPROFILE%
    else:
        base = Path.home()  # ~/.
    return base / ".consigaz-robo" / "playwright-profile"
```

Ambas as plataformas usam `Path.home() / ".consigaz-robo" / "playwright-profile"` — o prefixo `.` é oculto no macOS/Linux; no Windows fica em `C:\Users\<user>\.consigaz-robo\playwright-profile`.

### Seletores: Hierarquia `página > elemento`

```json
{
  "login": {
    "username": "input[name='username']",
    "password": "input[name='password']",
    "submit":   "button[type='submit']",
    "_session_sentinel": "#dashboard-header"
  },
  "cadastro_proposta": {
    "nome_titular": "#nome_titular",
    "cpf":          "input[data-field='cpf']",
    "valor":        "input[name='valor']",
    "btn_avancar":  "button:has-text('Avançar')"
  }
}
```

Chaves prefixadas com `_` são metadados do módulo (ex: `_session_sentinel`), não campos a preencher — `fill_form` ignora chaves que começam com `_`.

### Detecção de Sessão Expirada

Estratégia OR: URL check primeiro (barato), sentinel check em seguida (robusto para redirects silenciosos):

```python
def _is_login_page(page: Page, settings: Settings) -> bool:
    url = page.url
    for pattern in settings.web_login_url_patterns:
        if pattern in url:
            return True
    return False

def _check_session(page: Page, selectors: dict, settings: Settings) -> None:
    sentinel = selectors.get("login", {}).get("_session_sentinel")
    if _is_login_page(page, settings):
        raise LoginRequiredError(current_url=page.url)
    if sentinel:
        try:
            page.locator(sentinel).wait_for(timeout=3000)
        except PlaywrightTimeoutError:
            raise LoginRequiredError(current_url=page.url)
```

### Retry Exponencial

Usado apenas em operações que fazem requests HTTP (navigate_to, submit). Operações locais (fill, click) não têm retry — falha deve ser propagada imediatamente.

```python
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(PageLoadTimeoutError),
)
def navigate_to(url: str, page: Page, timeout: float = 30.0) -> None: ...
```

---

## Interfaces Públicas

### `web/session.py`

```python
def open_browser(settings: Settings) -> Page:
    """Abre chromium com perfil persistido; retorna Page pronta para uso."""

def close_browser() -> None:
    """Fecha contexto; no-op se não aberto."""
```

### `web/selectors.py`

```python
def load_selectors(path: str | Path | None = None) -> dict[str, dict[str, str]]:
    """Carrega config/selectors.json; lança FileNotFoundError ou SelectorLoadError."""

def get_selector(selectors: dict[str, dict[str, str]], page: str, key: str) -> str:
    """Retorna seletor; lança SelectorNotFoundError se page ou key não existir."""
```

### `web/navigation.py`

```python
def navigate_to(page: Page, url: str, timeout: float = 30.0) -> None:
    """Navega para URL e aguarda networkidle; lança PageLoadTimeoutError."""

def wait_for_selector(
    page: Page,
    selectors: dict[str, dict[str, str]],
    page_name: str,
    key: str,
    timeout: float = 15.0,
) -> Locator:
    """Aguarda seletor aparecer; lança SelectorNotFoundError."""
```

### `web/forms.py`

```python
def fill_form(
    page: Page,
    selectors: dict[str, dict[str, str]],
    page_name: str,
    data: dict[str, str | None],
) -> None:
    """Preenche campos: limpa → digita; ignora valores None; usa select_option para <select>."""

def handle_modal(page: Page) -> bool:
    """Fecha modal se presente; retorna True se fechou, False se não havia modal."""

def capture_transaction_id(
    page: Page,
    selectors: dict[str, dict[str, str]],
    page_name: str,
    key: str,
) -> str:
    """Extrai texto do campo; lança TransactionError se vazio."""
```

---

## Hierarquia de Exceções

```
WebError(RuntimeError)                   # base — qualquer falha do módulo web
├── LoginRequiredError                   # sessão expirada ou não iniciada
│       .current_url: str
├── SelectorNotFoundError                # chave/página ausente no JSON
│       .page: str
│       .key: str
├── SelectorLoadError                    # JSON malformado ou ilegível
│       .path: str
├── PageLoadTimeoutError                 # navigate_to excedeu timeout
│       .url: str
│       .elapsed: float
└── TransactionError                     # ID de transação vazio/ausente
        .page: str
        .key: str
```

---

## Configurações Novas em `settings.py`

```python
class Settings(BaseSettings):
    # ... campos existentes ...
    web_headless: bool = False
    web_login_url_patterns: list[str] = ["/login", "/auth", "/signin", "/entrar"]
    web_default_timeout: float = 15.0
    web_navigate_timeout: float = 30.0
    web_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    web_viewport_width: int = 1280
    web_viewport_height: int = 800
    web_locale: str = "pt-BR"
```

---

## Fluxo de Dados

```
Orquestrador
    │
    ├── open_browser(settings) ──────────────────→ Page
    │       └── launch_persistent_context(profile)
    │           └── _check_session() ──────────────→ LoginRequiredError (se expirada)
    │
    ├── load_selectors() ──────────────────────────→ selectors dict
    │
    ├── navigate_to(page, url) ─────────────────────→ PageLoadTimeoutError (se timeout)
    │
    ├── fill_form(page, selectors, page_name, data)
    │       └── get_selector(selectors, page_name, key) → SelectorNotFoundError
    │           └── locator(selector).fill(value)
    │
    ├── handle_modal(page) ─────────────────────────→ True/False
    │
    ├── capture_transaction_id(...) ────────────────→ str | TransactionError
    │
    └── close_browser()
```

---

## Mocks de Teste

Todos os testes rodam sem browser real. Padrão de mock:

```python
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_page():
    page = MagicMock()
    page.url = "https://app.consigaz.com.br/dashboard"
    page.locator.return_value.fill = MagicMock()
    page.locator.return_value.wait_for = MagicMock()
    return page

@pytest.fixture
def mock_context(mock_page):
    ctx = MagicMock()
    ctx.new_page.return_value = mock_page
    return ctx
```

`playwright.sync_api.sync_playwright` é mockado via `patch("web.session.sync_playwright")`.

---

## Notas de Implementação

- **Lazy import de playwright**: `from playwright.sync_api import sync_playwright` fica dentro de `open_browser()` para que o módulo possa ser importado em ambientes sem playwright instalado (testes que só precisam de `selectors.py` ou `exceptions.py`).
- **mypy + playwright**: adicionar `playwright.*` em `ignore_missing_imports` do `pyproject.toml` se stubs não estiverem disponíveis na versão instalada.
- **`fill_form` e campos `<select>`**: Playwright detecta o tipo via `element.evaluate("el => el.tagName")` — se `SELECT`, usar `.select_option(value=v)` em vez de `.fill(v)`.
