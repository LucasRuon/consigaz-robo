# M1 — Camada Desktop: Tasks

**Design**: `.specs/features/m1-desktop-layer/design.md`
**Status**: Draft

> Gate rápido (por módulo): `pytest tests/desktop/test_<módulo>.py -v`
> Gate completo: `pytest && ruff check src/desktop/ && mypy src/desktop/`

---

## Execution Plan

```
Phase 1 (Sequential — Foundation):
  T1 → T2

Phase 2 (Parallel — Adapter + Vision):
  T2 complete, then:
    ├── T3 [P]   platform/adapter.py + factory tests
    └── T4 [P]   vision.py + tests

Phase 3 (Parallel — Adapters macOS/Windows):
  T3 complete, then:
    ├── T5 [P]   platform/mac.py + tests
    └── T6 [P]   platform/win.py + tests

Phase 4 (Sequential — Interactions):
  T3 + T4 complete → T7   interactions.py + tests

Phase 5 (Sequential — Exports + Gate Final):
  T5 + T6 + T7 complete → T8
```

```
T1 → T2 ─┬─ T3 [P] ─┬─ T5 [P] ─┐
           │           └─ T6 [P] ─┼→ T8
           └─ T4 [P] ─────────────┤
                        T7 ────────┘
                       (dep: T3+T4)
```

---

## Task Breakdown

### T1: Scaffold do pacote `desktop`

**What**: Criar estrutura de diretórios e arquivos `__init__.py` do pacote `desktop`; registrar `src/desktop` em `pyproject.toml`; criar `tests/desktop/__init__.py`; adicionar dependências Windows-only.
**Where**:
- `src/desktop/__init__.py` (novo, vazio por ora)
- `src/desktop/platform/__init__.py` (novo, vazio)
- `tests/desktop/__init__.py` (novo, vazio)
- `pyproject.toml` (modificar: adicionar `src/desktop` em `packages` e deps Windows-only)
**Depends on**: Nenhuma
**Reuses**: Padrão de `src/platform_info/__init__.py` para estrutura de pacote
**Requirement**: DESK-01

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `src/desktop/__init__.py` existe (vazio)
- [ ] `src/desktop/platform/__init__.py` existe (vazio)
- [ ] `tests/desktop/__init__.py` existe (vazio)
- [ ] `pyproject.toml`: `src/desktop` adicionado em `[tool.hatch.build.targets.wheel] packages`
- [ ] `pyproject.toml`: `pygetwindow>=0.0.9; sys_platform == "win32"` adicionado em `dependencies`
- [ ] `pyproject.toml`: `pywin32>=306; sys_platform == "win32"` adicionado em `dependencies`
- [ ] Gate check: `python -c "import desktop"` retorna exit 0 (sem ImportError)

**Tests**: none
**Gate**: quick (`python -c "import desktop"`)

**Commit**: `feat(desktop): scaffold pacote desktop + deps Windows-only`

---

### T2: `desktop/exceptions.py` — exceções customizadas

**What**: Criar `src/desktop/exceptions.py` com as 4 exceções customizadas do módulo desktop; criar `tests/desktop/test_exceptions.py` com testes unitários.
**Where**:
- `src/desktop/exceptions.py` (novo)
- `tests/desktop/test_exceptions.py` (novo)
**Depends on**: T1
**Reuses**: `platform_info.UnsupportedPlatformError` como referência de padrão (mas NÃO reusar — criar exceção própria para independência do módulo)
**Requirement**: DESK-05, DESK-07, DESK-15

**Exceções a criar**:
```python
class PlatformError(RuntimeError): ...
class TemplateNotFoundError(RuntimeError):
    def __init__(self, template_path: str, screenshot_path: str, elapsed: float): ...
class InteractionError(RuntimeError):
    def __init__(self, action: str, template_path: str | None = None): ...
class UnsupportedPlatformError(RuntimeError): ...
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Todas as 4 classes de exceção definidas com atributos corretos
- [ ] `TemplateNotFoundError` expõe `.template_path`, `.screenshot_path`, `.elapsed`
- [ ] `InteractionError` expõe `.action`, `.template_path`
- [ ] Todas são subclasses de `RuntimeError`
- [ ] Gate check: `pytest tests/desktop/test_exceptions.py -v` → todos os testes passam
- [ ] Test count: ≥ 6 testes (issubclass, instanciação, atributos de cada exceção)

**Tests**: unit
**Gate**: quick (`pytest tests/desktop/test_exceptions.py -v`)

**Commit**: `feat(desktop): exceções customizadas PlatformError, TemplateNotFoundError, InteractionError`

---

### T3: `desktop/platform/adapter.py` — Protocol + factory [P]

**What**: Criar `PlatformAdapter` como `typing.Protocol` e a factory `get_platform_adapter()`; criar testes unitários da factory.
**Where**:
- `src/desktop/platform/adapter.py` (novo)
- `tests/desktop/test_platform_adapter.py` (novo)
**Depends on**: T2
**Reuses**: `platform_info.current_platform()` e `platform_info.Platform` para lógica de detecção; `tests/test_platform_info.py` como padrão de monkeypatch de `sys.platform`
**Requirement**: DESK-01, DESK-04

**Interface a criar**:
```python
class PlatformAdapter(Protocol):
    def launch_app(self, app_name: str) -> None: ...
    def focus_window(self, app_name: str) -> None: ...
    def modifier_key(self) -> str: ...
    def clipboard_copy(self) -> None: ...
    def clipboard_paste(self) -> None: ...

def get_platform_adapter() -> PlatformAdapter:
    """Factory: retorna MacAdapter em darwin, WindowsAdapter em win32."""
```

**Nota**: A factory importa `MacAdapter` e `WindowsAdapter` internamente (lazy) para evitar ImportError em SO que não tem as dependências (ex: pygetwindow no mac). Testes mockam `sys.platform` via `monkeypatch`.

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `PlatformAdapter` Protocol definido com todos os 5 métodos
- [ ] `get_platform_adapter()` retorna `MacAdapter` quando `sys.platform == "darwin"`
- [ ] `get_platform_adapter()` retorna `WindowsAdapter` quando `sys.platform == "win32"`
- [ ] `get_platform_adapter()` lança `UnsupportedPlatformError` em Linux
- [ ] Gate check: `pytest tests/desktop/test_platform_adapter.py -v` → todos passam
- [ ] Test count: ≥ 4 testes (darwin, win32, linux, tipo retornado)

**Tests**: unit
**Gate**: quick (`pytest tests/desktop/test_platform_adapter.py -v`)

**Commit**: `feat(desktop): PlatformAdapter Protocol + factory get_platform_adapter`

---

### T4: `desktop/vision.py` — wait_for_template [P]

**What**: Criar `wait_for_template()` com polling por OpenCV, resolução de path com fallback por SO, e tratamento de timeout com screenshot; criar testes unitários com mocks.
**Where**:
- `src/desktop/vision.py` (novo)
- `tests/desktop/test_vision.py` (novo)
**Depends on**: T2
**Reuses**: `src/logger/screenshot_hook.py` como referência para path `logs/errors/`; padrão de logger de `src/logger/setup.py`
**Requirement**: DESK-06, DESK-07, DESK-08, DESK-09

**Assinatura**:
```python
def wait_for_template(
    path: str | Path,
    timeout: float = 15.0,
    threshold: float = 0.8,
    poll_interval: float = 0.5,
) -> tuple[int, int]:
```

**Lógica de path (DESK-09)**:
```python
def _resolve_template_path(path: str | Path) -> Path:
    """Busca assets/templates/{sys.platform}/<name>, fallback assets/templates/<name>."""
    p = Path(path)
    platform_specific = p.parent / sys.platform / p.name
    if platform_specific.exists():
        return platform_specific
    return p
```

**Polling**: `time.monotonic()` para deadline; `time.sleep(poll_interval)` entre tentativas. **NUNCA** `time.sleep(timeout)`.

**Mocks necessários nos testes**:
- `pyautogui.screenshot` → retorna imagem fake (numpy array)
- `cv2.matchTemplate` → retorna score controlado
- `cv2.minMaxLoc` → retorna posição fake
- `pathlib.Path.exists` → controlar fallback de path
- Logger (para não criar arquivos reais em teste)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Retorna `(x, y)` quando score > threshold antes do timeout
- [ ] Lança `TemplateNotFoundError` com `.template_path`, `.screenshot_path`, `.elapsed` após timeout
- [ ] Lança `FileNotFoundError` imediatamente se arquivo não existe (antes de qualquer screenshot)
- [ ] Resolve path com fallback (darwin/ → raiz)
- [ ] Usa `time.monotonic()` — **nenhum** `time.sleep(timeout)` estático
- [ ] Gate check: `pytest tests/desktop/test_vision.py -v` → todos passam
- [ ] Test count: ≥ 7 testes (match imediato, timeout, arquivo ausente, fallback darwin, fallback raiz, threshold default, poll_interval)

**Tests**: unit
**Gate**: quick (`pytest tests/desktop/test_vision.py -v`)

**Commit**: `feat(desktop): wait_for_template com polling OpenCV e fallback de path por SO`

---

### T5: `desktop/platform/mac.py` — MacAdapter [P]

**What**: Implementar `MacAdapter` que satisfaz `PlatformAdapter`; criar testes unitários com mock de subprocess e pyautogui.
**Where**:
- `src/desktop/platform/mac.py` (novo)
- `tests/desktop/test_mac_adapter.py` (novo)
**Depends on**: T3
**Reuses**: `platform_info` como referência de padrão; `tests/test_platform_info.py` para padrão de mock de subprocess
**Requirement**: DESK-02, DESK-04

**Implementação**:
```python
class MacAdapter:
    def launch_app(self, app_name: str) -> None:
        # subprocess.run(["open", "-a", app_name], check=True, capture_output=True)
        # subprocess.CalledProcessError → PlatformError

    def focus_window(self, app_name: str) -> None:
        # osascript -e 'tell application "{app_name}" to activate'

    def modifier_key(self) -> str:
        return "cmd"

    def clipboard_copy(self) -> None:
        # pyautogui.hotkey("command", "c")

    def clipboard_paste(self) -> None:
        # pyautogui.hotkey("command", "v")
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `MacAdapter` satisfaz `PlatformAdapter` Protocol (mypy não reclama)
- [ ] `launch_app` chama `open -a <app>` via subprocess
- [ ] `focus_window` executa AppleScript via `osascript`
- [ ] `modifier_key()` retorna `"cmd"`
- [ ] Erros de subprocess são capturados e relançados como `PlatformError`
- [ ] Gate check: `pytest tests/desktop/test_mac_adapter.py -v` → todos passam
- [ ] Test count: ≥ 6 testes (launch ok, launch falha→PlatformError, focus ok, focus falha, modifier_key, clipboard)

**Tests**: unit
**Gate**: quick (`pytest tests/desktop/test_mac_adapter.py -v`)

**Commit**: `feat(desktop): MacAdapter com AppleScript/subprocess para macOS`

---

### T6: `desktop/platform/win.py` — WindowsAdapter [P]

**What**: Implementar `WindowsAdapter` que satisfaz `PlatformAdapter`; criar testes unitários com mock de pygetwindow e pyautogui.
**Where**:
- `src/desktop/platform/win.py` (novo)
- `tests/desktop/test_win_adapter.py` (novo)
**Depends on**: T3
**Reuses**: Padrão de `mac.py` (T5); `PlatformAdapter` Protocol de T3
**Requirement**: DESK-03, DESK-04

**Implementação**:
```python
class WindowsAdapter:
    def launch_app(self, app_name: str) -> None:
        # subprocess.Popen([app_name]) — lança PlatformError em FileNotFoundError

    def focus_window(self, app_name: str) -> None:
        # import pygetwindow as gw (lazy import — só instalado no Windows)
        # gw.getWindowsWithTitle(app_name)[0].activate()
        # IndexError (janela não encontrada) → PlatformError

    def modifier_key(self) -> str:
        return "ctrl"

    def clipboard_copy(self) -> None:
        # pyautogui.hotkey("ctrl", "c")

    def clipboard_paste(self) -> None:
        # pyautogui.hotkey("ctrl", "v")
```

**Nota crítica**: `import pygetwindow` deve ser LAZY (dentro do método `focus_window`) para que `win.py` possa ser importado em macOS nos testes, onde `pygetwindow` não está instalado. Usar `unittest.mock.patch` para mockar o módulo nos testes.

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `WindowsAdapter` satisfaz `PlatformAdapter` Protocol (mypy não reclama)
- [ ] `import desktop.platform.win` não lança ImportError em macOS (lazy import de pygetwindow)
- [ ] `modifier_key()` retorna `"ctrl"`
- [ ] Janela não encontrada → `PlatformError`
- [ ] Gate check: `pytest tests/desktop/test_win_adapter.py -v` → todos passam (rode em macOS com mocks)
- [ ] Test count: ≥ 6 testes (launch ok, launch falha, focus ok, focus falha→PlatformError, modifier_key, clipboard)

**Tests**: unit
**Gate**: quick (`pytest tests/desktop/test_win_adapter.py -v`)

**Commit**: `feat(desktop): WindowsAdapter com pygetwindow/pywin32 para Windows`

---

### T7: `desktop/interactions.py` — primitivas de UI

**What**: Criar as 4 primitivas de UI (`click_at_template`, `type_text`, `clear_field`, `extract_via_clipboard`); criar testes unitários com mocks; todas envolvidas em try/except obrigatório.
**Where**:
- `src/desktop/interactions.py` (novo)
- `tests/desktop/test_interactions.py` (novo)
**Depends on**: T3, T4
**Reuses**: `wait_for_template` de `vision.py`; `PlatformAdapter` de `platform/adapter.py`
**Requirement**: DESK-10, DESK-11, DESK-12, DESK-13, DESK-14

**Assinaturas**:
```python
def click_at_template(path: str | Path) -> None: ...
def type_text(text: str) -> None: ...
def clear_field(adapter: PlatformAdapter) -> None: ...
def extract_via_clipboard(adapter: PlatformAdapter) -> str: ...
```

**Regra NFR-5.2**: Cada função deve ter `try/except Exception as e: raise InteractionError(action=..., template_path=...) from e` envolvendo a chamada de UI.

**Casos especiais**:
- `type_text("")`: no-op, não chama pyautogui
- `extract_via_clipboard()`: retorna `""` se `pyperclip.paste()` retornar `""` (sem exceção)

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `click_at_template` chama `wait_for_template` → `pyautogui.click(x, y)`
- [ ] `type_text("")` é no-op (sem chamar pyautogui)
- [ ] `type_text("abc")` chama `pyautogui.write("abc", interval=0.05)`
- [ ] `clear_field` usa `adapter.modifier_key()` + `pyautogui.hotkey` + `pyautogui.press("delete")`
- [ ] `extract_via_clipboard` usa adapter + `pyperclip.paste()` e retorna string
- [ ] Toda falha de pyautogui/pyperclip é capturada e relançada como `InteractionError`
- [ ] Gate check: `pytest tests/desktop/test_interactions.py -v` → todos passam
- [ ] Test count: ≥ 10 testes (cada primitiva ok, type_text vazio, falha→InteractionError para pelo menos 2 funções)

**Tests**: unit
**Gate**: quick (`pytest tests/desktop/test_interactions.py -v`)

**Commit**: `feat(desktop): primitivas click_at_template, type_text, clear_field, extract_via_clipboard`

---

### T8: Exports públicos + gate completo do M1

**What**: Atualizar `src/desktop/__init__.py` com exports públicos das 3 features; rodar gate completo (pytest + ruff + mypy) e corrigir qualquer falha.
**Where**:
- `src/desktop/__init__.py` (modificar)
- `src/desktop/platform/__init__.py` (modificar se necessário)
**Depends on**: T5, T6, T7
**Reuses**: Padrão de `src/orchestrator/__init__.py` para exports
**Requirement**: todos (verificação final)

**Exports esperados em `desktop/__init__.py`**:
```python
from desktop.platform.adapter import PlatformAdapter, get_platform_adapter
from desktop.vision import wait_for_template
from desktop.interactions import (
    click_at_template,
    type_text,
    clear_field,
    extract_via_clipboard,
)
from desktop.exceptions import (
    PlatformError,
    TemplateNotFoundError,
    InteractionError,
    UnsupportedPlatformError,
)
```

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `from desktop import get_platform_adapter, wait_for_template, click_at_template` funciona
- [ ] `pytest tests/desktop/ -v` → todos passam (≥ 39 testes: soma dos gates anteriores)
- [ ] `pytest` (suite completa) → todos os 72 testes de M0 continuam passando + novos testes de M1
- [ ] `ruff check src/desktop/` → zero erros
- [ ] `mypy src/desktop/` → zero erros (strict mode)
- [ ] Nenhuma coordenada hardcoded em nenhum arquivo de `src/desktop/`
- [ ] Nenhum `time.sleep` > 1s em `vision.py`

**Tests**: integration (smoke)
**Gate**: full (`pytest && ruff check src/desktop/ && mypy src/desktop/`)

**Commit**: `feat(desktop): exports públicos M1 + gate completo verde`

---

## Parallel Execution Map

```
Phase 1 (Sequential — Foundation):
  T1 → T2

Phase 2 (Parallel — after T2):
  T2 complete:
    ├── T3 [P]   platform/adapter.py
    └── T4 [P]   vision.py

Phase 3 (Parallel — after T3):
  T3 complete:
    ├── T5 [P]   platform/mac.py
    └── T6 [P]   platform/win.py

Phase 4 (Sequential — after T3+T4):
  T3+T4 complete → T7   interactions.py

Phase 5 (Sequential — after T5+T6+T7):
  T5+T6+T7 complete → T8   exports + gate final
```

**Constraint T4 vs T3**: T3 e T4 são paralelos (ambos dependem apenas de T2). T4 não usa `PlatformAdapter` — usa `sys.platform` diretamente para resolução de path.

**Constraint T5 vs T6**: Paralelos — implementam adapters distintos, arquivos distintos, testes distintos, sem estado compartilhado.

---

## Task Granularity Check

| Task | Escopo | Status |
|---|---|---|
| T1: Scaffold pacote | 3 `__init__.py` + pyproject.toml tweak | ✅ Granular |
| T2: exceptions.py | 1 arquivo, 4 classes | ✅ Granular |
| T3: adapter.py | 1 arquivo, 1 Protocol + 1 function | ✅ Granular |
| T4: vision.py | 1 arquivo, 1 função principal | ✅ Granular |
| T5: mac.py | 1 arquivo, 1 classe | ✅ Granular |
| T6: win.py | 1 arquivo, 1 classe | ✅ Granular |
| T7: interactions.py | 1 arquivo, 4 funções coesas | ✅ OK (4 funções no mesmo arquivo é coeso) |
| T8: exports + gate | 1 arquivo modificado + verificação | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagrama mostra | Status |
|---|---|---|---|
| T1 | Nenhuma | Início | ✅ |
| T2 | T1 | T1 → T2 | ✅ |
| T3 [P] | T2 | T2 → T3 | ✅ |
| T4 [P] | T2 | T2 → T4 | ✅ |
| T5 [P] | T3 | T3 → T5 | ✅ |
| T6 [P] | T3 | T3 → T6 | ✅ |
| T7 | T3, T4 | T3+T4 → T7 | ✅ |
| T8 | T5, T6, T7 | T5+T6+T7 → T8 | ✅ |

---

## Test Co-location Validation

> TESTING.md não existe em `.specs/codebase/`. Padrão inferido dos testes de M0: pytest, unit tests com monkeypatch/mock, sem testes de integração com hardware real.

| Task | Camada criada | Tipo requerido | Task diz | Status |
|---|---|---|---|---|
| T1 | Scaffold (sem lógica) | none | none | ✅ |
| T2 | exceptions.py | unit | unit | ✅ |
| T3 | platform/adapter.py (Protocol + factory) | unit | unit | ✅ |
| T4 | vision.py (lógica OpenCV) | unit | unit | ✅ |
| T5 | platform/mac.py | unit | unit | ✅ |
| T6 | platform/win.py | unit | unit | ✅ |
| T7 | interactions.py | unit | unit | ✅ |
| T8 | __init__.py (exports) | integration smoke | integration | ✅ |
