# M0 — Fundação Cross-Platform Tasks

**Design**: `.specs/features/m0-foundation/design.md`
**Status**: Draft

---

## Test Coverage Matrix (inline — greenfield)

Como `.specs/codebase/TESTING.md` ainda não existe, defino aqui o contrato de testes do M0 (será promovido para `TESTING.md` ao fim do milestone).

| Code Layer | Test Type | Parallel-Safe | Justificativa |
|---|---|---|---|
| `src/platform_info.py` | unit | Yes | Puro, sem I/O |
| `src/config/settings.py` | unit | Yes | Mock de env vars via `monkeypatch` |
| `src/config/keyring_source.py` | unit | Yes | Mock de `keyring.get_password` |
| `src/config/display.py` | unit | Yes | Função pura sobre `Settings` |
| `src/logger/processors.py` | unit | Yes | Função pura sobre dict |
| `src/logger/setup.py` | integration | No | Toca filesystem (cria arquivos em `tmp_path`); compartilha config global do structlog |
| `src/logger/screenshot_hook.py` | integration | No | Monkeypatch `sys.excepthook` (global) + filesystem |
| `src/orchestrator/boot.py` | integration | No | Compõe config + logger + filesystem |
| `src/orchestrator/cli.py` | unit | Yes | argparse com args injetados |
| `src/orchestrator/__main__.py` | e2e | No | Subprocess real; competiria por stdout |
| `tasks.py` (invoke) | none | — | Manual: documentado em CHECKS.md |
| Docs (`README.md`, `CHECKS.md`) | none | — | Revisão humana |

### Gate Check Commands

| Gate | Comando | Quando usar |
|---|---|---|
| `quick` | `inv test -- tests/test_<arquivo>.py` | Após mudança em uma unit |
| `full` | `inv test && inv lint && inv typecheck` | Antes de fechar a task |
| `e2e` | `inv smoke` (definido em T3: roda `python -m orchestrator --help` em subprocess) | Final do milestone |

---

## Execution Plan

### Phase 1: Repo bootstrap (Sequential)

```
T1 → T2 → T3
```

### Phase 2: Módulos base (Parallel após T2)

```
        ┌→ T4  [P] (platform_info)
        ├→ T5  [P] (settings sem keyring)
T2 ────┼→ T6  [P] (keyring_source)
        └→ T9  [P] (logger processors)
```

### Phase 3: Integração de subsistemas (Sequential dentro de cada trilha; trilhas independentes em paralelo)

```
Trilha config:  T5, T6 → T7 → T8
Trilha logger:  T9    → T10 → T11   (T11 também depende de T2 para criar logs/errors/)
```

### Phase 4: Orchestrator (Sequential)

```
T4, T7, T8, T10, T11 ──→ T12 ──→ T13 ──→ T14
```

### Phase 5: Documentação & validação final (Parallel)

```
T14 ──┬→ T15 [P] (README)
       └→ T16 [P] (CHECKS.md + smoke task em invoke)
```

---

## Task Breakdown

### T1: Inicializar repo, .gitignore e pyproject.toml

**What**: Criar `pyproject.toml` declarando metadata, Python ≥3.11, dependências runtime e dev. Criar `.gitignore` típico Python+macOS+Windows. Inicializar `git`. Rodar `uv sync` para gerar `uv.lock`.
**Where**: `pyproject.toml`, `.gitignore`, `uv.lock` (gerado), `.python-version` (gerado)
**Depends on**: None
**Reuses**: Templates padrão de `.gitignore` (github/gitignore Python.gitignore)
**Requirement**: M0-01, M0-02, M0-03, M0-04

**Tools**:
- MCP: NONE
- Skill: NONE

**Deps runtime**: `pydantic>=2.5`, `pydantic-settings>=2.1`, `keyring>=24`, `structlog>=24`, `pyautogui>=0.9.54`, `opencv-python>=4.9`, `playwright>=1.40`, `pandas>=2.2`, `openai>=1.12`, `tenacity>=8.2`, `invoke>=2.2`

**Deps dev**: `pytest>=8`, `pytest-cov>=4`, `ruff>=0.4`, `mypy>=1.10`, `types-keyring`

**Done when**:
- [ ] `pyproject.toml` válido com `requires-python = ">=3.11"` e `[project.optional-dependencies.dev]`
- [ ] `.gitignore` cobre `.venv/`, `__pycache__/`, `*.pyc`, `logs/`, `.DS_Store`, `Thumbs.db`, `uv.lock` NÃO ignorado
- [ ] `git init` executado, primeiro commit feito
- [ ] `uv sync` completa sem erro em macOS (validar manualmente; Windows fica para CHECKS.md)
- [ ] `uv lock --check` confirma lock atualizado
- [ ] Smoke: `uv run python -c "import cv2, pyautogui, pandas, keyring, pydantic, structlog, openai, tenacity, invoke; print('ok')"` imprime `ok`

**Tests**: none (configuração de repo)
**Gate**: build (o próprio `uv sync` é o gate)

**Verify**:
```bash
uv sync
uv run python -c "import cv2, pyautogui, pandas, keyring, pydantic, structlog, openai, tenacity, invoke; print('ok')"
```
Esperado: `ok` impresso, exit 0.

**Commit**: `chore: bootstrap repo with uv, pyproject.toml e .gitignore`

---

### T2: Criar estrutura de diretórios e arquivos vazios

**What**: Criar todos os diretórios do projeto e arquivos `__init__.py` vazios. Criar `.env.example` com placeholders dos segredos.
**Where**: `src/orchestrator/`, `src/config/`, `src/logger/`, `src/{__init__,platform_info}.py`, `tests/`, `assets/templates/`, `logs/errors/`, `.env.example`
**Depends on**: T1
**Reuses**: Estrutura definida em design.md
**Requirement**: M0-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Todos os diretórios listados existem
- [ ] `__init__.py` vazio em cada pacote (`src/`, `src/orchestrator/`, `src/config/`, `src/logger/`, `tests/`)
- [ ] `assets/templates/.gitkeep` e `logs/errors/.gitkeep` existem (mantém pastas no git)
- [ ] `.env.example` lista chaves: `OPENAI_API_KEY=`, `DESKTOP_APP_PASSWORD=`, `WEB_PLATFORM_PASSWORD=`, `LOG_LEVEL=INFO`, `PROFILE=dev`
- [ ] `pyproject.toml` declara `[tool.setuptools.packages.find] where = ["src"]` (ou equivalente em hatchling/uv)
- [ ] `uv run python -c "import orchestrator, config, logger, platform_info"` funciona

**Tests**: none (estrutura)
**Gate**: build (imports funcionando)

**Verify**:
```bash
uv run python -c "import orchestrator, config, logger, platform_info; print('imports ok')"
```

**Commit**: `chore: criar estrutura de pacotes src/ e .env.example`

---

### T3: Criar `tasks.py` com comandos invoke cross-platform

**What**: Definir `tasks.py` com todas as tasks do projeto usando `invoke`. Validar que rodam em mac e win.
**Where**: `tasks.py`
**Depends on**: T2
**Reuses**: API do `invoke`
**Requirement**: M0-20, M0-21, M0-22, M0-23

**Tools**:
- MCP: `context7` (para `invoke` se necessário)
- Skill: NONE

**Tasks a definir** (mínimo):
- `inv setup` → `uv sync`
- `inv test` (com flag `--only PATH` opcional) → `pytest`
- `inv lint` → `ruff check src tests`
- `inv format` → `ruff format src tests`
- `inv typecheck` → `mypy src`
- `inv smoke` → roda `python -m orchestrator --help` em subprocess e valida exit 0
- `inv clean` → remove `.pytest_cache`, `__pycache__`, `.mypy_cache`, `.ruff_cache`

**Done when**:
- [ ] Todos os comandos acima existem em `tasks.py` com docstrings
- [ ] `inv --list` mostra todas as tasks
- [ ] `inv lint` retorna exit 0 (código atual está limpo)
- [ ] `inv format` é idempotente (segunda execução não muda nada)
- [ ] `inv typecheck` retorna exit 0 (mesmo sem código, `mypy src` em diretório vazio passa)
- [ ] Comandos usam `pathlib.Path` (não strings); funcionam com backslash no Windows

**Tests**: none (manual via CHECKS.md)
**Gate**: full → `inv lint && inv typecheck` passam

**Verify**:
```bash
uv run inv --list
uv run inv lint
uv run inv typecheck
```

**Commit**: `chore: adicionar tasks.py com comandos invoke (setup/test/lint/format/typecheck/smoke/clean)`

---

### T4: Implementar `src/platform_info.py` + testes [P]

**What**: Módulo único que detecta SO e expõe enum + constantes derivadas.
**Where**: `src/platform_info.py`, `tests/test_platform_info.py`
**Depends on**: T2
**Reuses**: stdlib `sys`, `platform`, `enum`
**Requirement**: (suporta M0-05 indiretamente — `is_supported` é usado no boot)

**Tools**:
- MCP: NONE
- Skill: NONE

**Interface**:
```python
class Platform(Enum):
    DARWIN = "darwin"
    WIN32 = "win32"

def current_platform() -> Platform: ...
def is_supported() -> bool: ...
MODIFIER_KEY: str  # "cmd" ou "ctrl"
```

**Done when**:
- [ ] `current_platform()` retorna `Platform.DARWIN` em mac, `Platform.WIN32` em win, lança `UnsupportedPlatformError` (custom) em outros
- [ ] `is_supported()` retorna False em Linux, Windows ARM64
- [ ] `MODIFIER_KEY` é constante de módulo derivada no import time
- [ ] Testes parametrizados cobrem: darwin → cmd, win32 → ctrl, linux → exceção, win-arm64 → not supported
- [ ] Mock de `sys.platform` e `platform.machine()` via `monkeypatch`
- [ ] `mypy --strict` passa neste arquivo
- [ ] Test count: ≥5 testes passam

**Tests**: unit
**Gate**: quick → `inv test -- tests/test_platform_info.py`

**Verify**:
```bash
uv run inv test -- tests/test_platform_info.py -v
```

**Commit**: `feat(platform): detectar SO e expor enum Platform + MODIFIER_KEY`

---

### T5: Implementar `src/config/settings.py` (sem keyring source ainda) + testes [P]

**What**: `Settings(BaseSettings)` com todos os campos, sem o source de keyring ainda. Source de keyring entra em T7.
**Where**: `src/config/settings.py`, `src/config/__init__.py`, `tests/test_config_settings.py`
**Depends on**: T2
**Reuses**: `pydantic`, `pydantic-settings`
**Requirement**: M0-07 (parcial — carregamento de `.env`), M0-09 (validação de obrigatórios)

**Interface** (campos do design):
```python
class Settings(BaseSettings):
    profile: Literal["dev", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_dir: Path = Path("logs")
    openai_api_key: SecretStr | None = None
    desktop_app_password: SecretStr | None = None
    web_platform_password: SecretStr | None = None
    sensitive_keys: frozenset[str] = DEFAULT_SENSITIVE_KEYS

    model_config = SettingsConfigDict(env_file=".env", extra="forbid", ...)
```

**Done when**:
- [ ] Classe `Settings` definida com todos os campos do design
- [ ] `Settings()` carrega de `.env` (testar com `tmp_path` e `monkeypatch.chdir`)
- [ ] `Settings(_env_file=...)` permite injeção em testes
- [ ] Em `profile="prod"`, campos `openai_api_key` etc. ficam **obrigatórios** (via `model_validator` ou Field condicional) — lança `ValidationError` com nome do campo
- [ ] Em `profile="dev"`, segredos None são aceitos
- [ ] Test count: ≥6 testes (dev sem segredos, prod sem segredos = erro, prod com segredos = ok, env override, .env load, extra="forbid")
- [ ] `mypy --strict` passa

**Tests**: unit
**Gate**: quick → `inv test -- tests/test_config_settings.py`

**Verify**:
```bash
uv run inv test -- tests/test_config_settings.py -v
```

**Commit**: `feat(config): adicionar Settings (Pydantic) carregando de .env`

---

### T6: Implementar `src/config/keyring_source.py` + testes [P]

**What**: Custom source para `pydantic-settings` que lê segredos do `keyring` do SO. Service name = `"consigaz-robo"`.
**Where**: `src/config/keyring_source.py`, `tests/test_config_keyring_source.py`
**Depends on**: T2
**Reuses**: `pydantic_settings.PydanticBaseSettingsSource`, `keyring`
**Requirement**: M0-07, M0-12 (precedência), M0-08 (fallback)

**Interface**:
```python
KEYRING_SERVICE = "consigaz-robo"

class KeyringSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(self, field, field_name): ...
    def __call__(self) -> dict[str, Any]: ...
```

**Done when**:
- [ ] Para cada field, tenta `keyring.get_password(KEYRING_SERVICE, field_name)`
- [ ] Se `keyring.errors.KeyringError`, captura e retorna `{}` (fallback silencioso)
- [ ] Se valor é `None`, não inclui no dict (deixa fallback agir)
- [ ] Service name constante exportada para testes/docs
- [ ] Tests cobrem: keyring com valor → vence; keyring vazio → vazio; keyring lança erro → vazio sem propagar
- [ ] Test count: ≥4 testes (mock de `keyring.get_password` via `monkeypatch.setattr`)
- [ ] `mypy --strict` passa

**Tests**: unit
**Gate**: quick → `inv test -- tests/test_config_keyring_source.py`

**Verify**:
```bash
uv run inv test -- tests/test_config_keyring_source.py -v
```

**Commit**: `feat(config): KeyringSettingsSource lendo Keychain/Credential Manager via lib keyring`

---

### T7: Integrar `KeyringSettingsSource` em `Settings` (precedência) + testes

**What**: Override de `settings_customise_sources` em `Settings` para que o `KeyringSettingsSource` venha após `init_settings` e antes de `dotenv_settings`. Validar precedência ponta-a-ponta.
**Where**: `src/config/settings.py` (modificar), `tests/test_config_settings.py` (estender)
**Depends on**: T5, T6
**Reuses**: ambos
**Requirement**: M0-07, M0-12, M0-08

**Done when**:
- [ ] Método `settings_customise_sources` retorna tupla na ordem: `init_settings`, `KeyringSettingsSource(...)`, `dotenv_settings`, `env_settings`, `file_secret_settings`
- [ ] Teste: segredo no keyring mock E no `.env` → valor do keyring vence
- [ ] Teste: segredo só no `.env` → `.env` vence
- [ ] Teste: segredo só no keyring mock → keyring vence
- [ ] Teste: nenhum dos dois em `profile=prod` → `ValidationError`
- [ ] Test count: ≥4 testes novos (somando a T5)
- [ ] `inv test -- tests/test_config_settings.py` total ≥10 passam

**Tests**: integration (compõe Settings + KeyringSource)
**Gate**: full → `inv test && inv lint && inv typecheck`

**Verify**:
```bash
uv run inv test -- tests/test_config_settings.py tests/test_config_keyring_source.py -v
```

**Commit**: `feat(config): wirear KeyringSettingsSource em Settings com precedência keyring > .env`

---

### T8: Implementar `src/config/display.py` (mascaramento) + testes

**What**: Função `show(settings: Settings) -> str` que retorna representação humana com `SecretStr` mascarado.
**Where**: `src/config/display.py`, `tests/test_config_display.py`
**Depends on**: T5
**Reuses**: `pydantic.SecretStr` (já mascara em `repr`, mas formatamos custom)
**Requirement**: M0-11

**Interface**:
```python
def show(settings: Settings) -> str:
    """Retorna multi-linha 'campo: valor' com SecretStr → 'sk-***' (mostra prefixo + ***)."""
```

**Done when**:
- [ ] Para campos `SecretStr` com valor: mostra primeiros 3 chars + `***` (ex: `sk-***`)
- [ ] Para campos `SecretStr` None: mostra `<não configurado>`
- [ ] Para campos não-secret: mostra valor cru
- [ ] Teste: `show(Settings(openai_api_key=SecretStr("sk-test123")))` contém `sk-***`, NÃO contém `test123`
- [ ] Teste: garantir que valor cru NUNCA aparece (compara com `not in`)
- [ ] Test count: ≥4 testes
- [ ] `mypy --strict` passa

**Tests**: unit
**Gate**: quick → `inv test -- tests/test_config_display.py`

**Verify**:
```bash
uv run inv test -- tests/test_config_display.py -v
```

**Commit**: `feat(config): adicionar display.show() mascarando SecretStr`

---

### T9: Implementar `src/logger/processors.py` (sanitização) + testes [P]

**What**: Processador structlog que mascara valores cujas **chaves** combinam com `sensitive_keys` (case-insensitive, substring).
**Where**: `src/logger/processors.py`, `src/logger/__init__.py`, `tests/test_logger_processors.py`
**Depends on**: T2
**Reuses**: convenção de processador do structlog (`def proc(logger, method, event_dict): ...`)
**Requirement**: M0-17, M0-04 (sanitização) — parte de M0-13..19

**Interface**:
```python
DEFAULT_SENSITIVE_KEYS = frozenset({"password", "passwd", "secret", "token",
                                     "api_key", "apikey", "authorization",
                                     "cpf", "cnpj", "rg"})

def make_sanitizer(sensitive_keys: frozenset[str] = DEFAULT_SENSITIVE_KEYS):
    """Retorna processor structlog que mascara valores de chaves sensíveis."""
    def processor(logger, method, event_dict):
        # match case-insensitive por substring no nome da chave
        ...
        return event_dict
    return processor
```

**Done when**:
- [ ] Match case-insensitive: `Password`, `PASSWORD`, `password` todos casam com `password`
- [ ] Match por substring: `openai_api_key` casa com `api_key`
- [ ] Mascaramento: valor virou `"***"` (string fixa, não revela tamanho)
- [ ] Não-recursivo em v1: dicts/listas nested NÃO são processados (registrar limitação em STATE.md)
- [ ] Test count: ≥6 (chave exata, case-insensitive, substring, não-match, dict raso, custom sensitive_keys)
- [ ] `mypy --strict` passa

**Tests**: unit
**Gate**: quick → `inv test -- tests/test_logger_processors.py`

**Verify**:
```bash
uv run inv test -- tests/test_logger_processors.py -v
```

**Commit**: `feat(logger): processador structlog para sanitizar chaves sensíveis`

---

### T10: Implementar `src/logger/setup.py` (dual sink: .log + .json) + testes

**What**: `setup_logging(routine, log_dir, level)` configura structlog com dois sinks: console renderer → `.log`, JSON renderer → `.json`. Função `get_logger(name)` retorna BoundLogger.
**Where**: `src/logger/setup.py`, `tests/test_logger_setup.py`
**Depends on**: T9
**Reuses**: `structlog.processors.{TimeStamper, JSONRenderer}`, `structlog.dev.ConsoleRenderer`
**Requirement**: M0-13, M0-14, M0-16

**Interface**:
```python
def setup_logging(routine: str, log_dir: Path = Path("logs"),
                  level: str = "INFO",
                  sensitive_keys: frozenset[str] | None = None) -> None: ...

def get_logger(name: str) -> structlog.BoundLogger: ...
```

**Done when**:
- [ ] Cria `log_dir/` se não existir
- [ ] Gera dois arquivos: `<timestamp>_<routine>.log` (humano) e `<timestamp>_<routine>.json` (JSON one-per-line)
- [ ] Mesmo evento de log aparece nos dois arquivos
- [ ] Nível respeita parâmetro `level` (valida com `DEBUG` vs `INFO`)
- [ ] Pipeline inclui o sanitizer de T9
- [ ] Encoding UTF-8 explícito (sem mojibake no Windows)
- [ ] Test usa `tmp_path` para isolar; verifica conteúdo de ambos arquivos
- [ ] Test: logar `{"password": "abc"}` → ambos arquivos mostram `"***"`, nunca `"abc"`
- [ ] Test count: ≥5
- [ ] `mypy --strict` passa

**Tests**: integration (filesystem + structlog global state)
**Gate**: full → `inv test && inv lint && inv typecheck`

**Verify**:
```bash
uv run inv test -- tests/test_logger_setup.py -v
```

**Commit**: `feat(logger): setup_logging com dual sink (.log humano + .json estruturado)`

---

### T11: Implementar `src/logger/screenshot_hook.py` (excepthook + captura) + testes

**What**: `install_excepthook(routine, errors_dir)` instala `sys.excepthook` que: tira screenshot via `pyautogui`, salva em `errors_dir`, registra no logger; se a captura falhar, loga warning mas re-raise a exceção original.
**Where**: `src/logger/screenshot_hook.py`, `tests/test_logger_screenshot_hook.py`
**Depends on**: T2, T10
**Reuses**: `pyautogui.screenshot()`
**Requirement**: M0-15, M0-18, M0-19

**Interface**:
```python
def install_excepthook(routine: str, errors_dir: Path = Path("logs/errors")) -> None: ...
def take_screenshot(path: Path) -> bool:
    """Retorna True em sucesso, False em falha (sem propagar exceção)."""
```

**Done when**:
- [ ] `install_excepthook` substitui `sys.excepthook` por wrapper que faz: log de erro → screenshot → re-raise via excepthook anterior
- [ ] `take_screenshot` retorna `True/False` sem propagar
- [ ] Arquivo gerado: `<timestamp>_<routine>.png` em `errors_dir`
- [ ] Cria `errors_dir/` se não existir
- [ ] Test usa `monkeypatch.setattr("pyautogui.screenshot", fake)` para evitar UI real
- [ ] Test: screenshot OK → arquivo criado + log de info
- [ ] Test: screenshot falha (mock lança) → log de warning, função retorna False, exceção original não mascarada
- [ ] Test: hook é instalado e desinstalado em fixture (limpar `sys.excepthook` no teardown)
- [ ] Test count: ≥4
- [ ] `mypy --strict` passa

**Tests**: integration (filesystem + sys global)
**Gate**: full → `inv test && inv lint && inv typecheck`

**Verify**:
```bash
uv run inv test -- tests/test_logger_screenshot_hook.py -v
```

**Commit**: `feat(logger): excepthook que captura screenshot em exceção não tratada`

---

### T12: Implementar `src/orchestrator/boot.py` + testes

**What**: `boot()` faz: detecta plataforma (T4) → carrega Settings (T7) → setup logger (T10) → instala excepthook (T11). Retorna `BootContext`.
**Where**: `src/orchestrator/boot.py`, `tests/test_orchestrator_boot.py`
**Depends on**: T4, T7, T8, T10, T11
**Reuses**: tudo de Phases 2-3
**Requirement**: M0-05 (compila e executa), M0-09 (falha em segredo faltando)

**Interface**:
```python
@dataclass(frozen=True)
class BootContext:
    platform: Platform
    settings: Settings
    routine: str
    log_dir: Path

def boot(routine: str = "default") -> BootContext: ...
```

**Done when**:
- [ ] `boot("default")` em `profile=dev` sem segredos retorna `BootContext` válido
- [ ] `boot()` em `profile=prod` sem segredos lança `ValidationError` (do Settings)
- [ ] `boot()` em plataforma não suportada lança `UnsupportedPlatformError`
- [ ] Logger é setupado com sucesso (arquivos em `log_dir/`)
- [ ] Excepthook está instalado após boot
- [ ] Test count: ≥4
- [ ] `mypy --strict` passa

**Tests**: integration
**Gate**: full → `inv test && inv lint && inv typecheck`

**Verify**:
```bash
uv run inv test -- tests/test_orchestrator_boot.py -v
```

**Commit**: `feat(orchestrator): boot() compõe detecção de plataforma, settings, logger e excepthook`

---

### T13: Implementar `src/orchestrator/cli.py` (argparse + --help) + testes

**What**: CLI com argparse. Comandos: `--help` (default na ausência de args), `--routine NAME` (placeholder, despacho real fica M4), `--dry-run` (flag).
**Where**: `src/orchestrator/cli.py`, `tests/test_orchestrator_cli.py`
**Depends on**: T12
**Reuses**: stdlib `argparse`
**Requirement**: M0-05

**Interface**:
```python
def build_parser() -> argparse.ArgumentParser: ...
def main(argv: list[str] | None = None) -> int: ...
```

**Done when**:
- [ ] `main(["--help"])` imprime usage e retorna 0
- [ ] `main([])` (sem args) também imprime help e retorna 0 (decisão UX explícita)
- [ ] `main(["--routine", "default"])` chama `boot("default")` (mock no teste) e retorna 0
- [ ] Erros de boot retornam exit code não-zero (mapeamento: ValidationError → 2, UnsupportedPlatform → 3, outros → 1)
- [ ] Test usa `capsys` para capturar stdout
- [ ] Test count: ≥5
- [ ] `mypy --strict` passa

**Tests**: unit (argparse com args injetados)
**Gate**: quick → `inv test -- tests/test_orchestrator_cli.py`

**Verify**:
```bash
uv run inv test -- tests/test_orchestrator_cli.py -v
```

**Commit**: `feat(orchestrator): CLI com argparse (--help, --routine, --dry-run)`

---

### T14: Implementar `src/orchestrator/__main__.py` + smoke e2e

**What**: Entry point para `python -m orchestrator`. Apenas chama `sys.exit(main(sys.argv[1:]))`.
**Where**: `src/orchestrator/__main__.py`, `tests/test_orchestrator_e2e.py`
**Depends on**: T13
**Reuses**: T13
**Requirement**: M0-05

**Done when**:
- [ ] `__main__.py` tem 3 linhas no máximo: import, chamada, exit
- [ ] Teste e2e via `subprocess.run([sys.executable, "-m", "orchestrator", "--help"], ...)`
- [ ] Exit code = 0
- [ ] Stdout contém `"usage:"`
- [ ] Test count: ≥2 (--help, sem args)

**Tests**: e2e
**Gate**: full + e2e → `inv test && inv lint && inv typecheck && inv smoke`

**Verify**:
```bash
uv run python -m orchestrator --help
uv run inv smoke
```
Esperado: usage impresso, exit 0 nos dois.

**Commit**: `feat(orchestrator): __main__.py + teste e2e via subprocess`

---

### T15: Escrever README.md com seções por SO [P]

**What**: README com: visão geral, pré-requisitos, instalação macOS (Python 3.11+, uv, Acessibilidade + Gravação de Tela), instalação Windows (Python 3.11+ com PATH, uv, UAC), comandos comuns (`inv setup`, `inv test`, `python -m orchestrator --help`), troubleshooting.
**Where**: `README.md`
**Depends on**: T14
**Reuses**: nada
**Requirement**: M0-24, M0-25, M0-26

**Done when**:
- [ ] Seções: Visão geral, Pré-requisitos, Instalação macOS, Instalação Windows, Comandos, Estrutura, Troubleshooting
- [ ] Instruções macOS incluem: como instalar Python 3.11+ (recomendar `pyenv` ou installer python.org), `curl -LsSf https://astral.sh/uv/install.sh | sh`, conceder Acessibilidade + Gravação de Tela ao terminal/iTerm (passo a passo em System Settings)
- [ ] Instruções Windows incluem: instalar Python 3.11+ marcando "Add to PATH", `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, nota sobre UAC
- [ ] Troubleshooting: erro "no wheel for arch", erro de permissão de screenshot, encoding no Windows
- [ ] Revisão humana

**Tests**: none
**Gate**: none (revisão manual)

**Verify**: Revisar visualmente, validar links, validar comandos PowerShell em VM Windows se possível.

**Commit**: `docs: README com instalação cross-platform e troubleshooting`

---

### T16: Criar CHECKS.md + validar manualmente em mac e win [P]

**What**: `CHECKS.md` com checklist reproduzível. Executar o checklist em pelo menos uma máquina mac e uma win.
**Where**: `CHECKS.md`
**Depends on**: T14
**Reuses**: estrutura definida em design.md
**Requirement**: Closure do M0

**Done when**:
- [ ] `CHECKS.md` lista: `uv sync`, `inv test`, `inv lint`, `inv typecheck`, `python -m orchestrator --help`, logs criados, screenshot em erro forçado — para macOS E Windows
- [ ] Validação manual completa em macOS (todas as caixas marcadas) — registrar data + arch
- [ ] Validação manual completa em Windows (todas as caixas marcadas) — registrar data + versão
- [ ] Qualquer divergência vira issue ou task em `STATE.md` → TODOs
- [ ] Atualizar `.specs/project/STATE.md` com data de validação cross-platform de M0

**Tests**: none (manual)
**Gate**: e2e (manual full check)

**Verify**: Caixas marcadas + assinatura humana no CHECKS.md.

**Commit**: `docs: CHECKS.md com checklist de validação cross-platform`

---

## Parallel Execution Map

```
Phase 1 (Sequential):
  T1 ──→ T2 ──→ T3

Phase 2 (Parallel após T2):
  T2 done, então:
    ├── T4 [P]  platform_info
    ├── T5 [P]  settings (sem keyring)
    ├── T6 [P]  keyring_source
    └── T9 [P]  logger processors

Phase 3 (trilhas paralelas, sequencial dentro):
  Trilha config:  (T5, T6) ──→ T7 ──→ T8
  Trilha logger:  T9 ──→ T10 ──→ T11

Phase 4 (Sequential):
  (T4, T8, T11) done, então:
    T12 ──→ T13 ──→ T14

Phase 5 (Parallel após T14):
    ├── T15 [P]  README
    └── T16 [P]  CHECKS.md
```

---

## Granularity Check

| Task | Escopo | Status |
|---|---|---|
| T1: pyproject + .gitignore + uv lock | 1 setup atômico | ✅ |
| T2: estrutura de pastas + __init__.py | 1 setup atômico | ✅ |
| T3: tasks.py (invoke) | 1 arquivo, ~7 tasks coesas | ✅ |
| T4: platform_info.py | 1 módulo único | ✅ |
| T5: Settings sem keyring | 1 classe | ✅ |
| T6: KeyringSettingsSource | 1 classe | ✅ |
| T7: integração T5+T6 | 1 método override | ✅ |
| T8: display.show() | 1 função | ✅ |
| T9: sanitizer | 1 fábrica de processor | ✅ |
| T10: setup_logging + get_logger | 1 módulo, 2 funções coesas | ✅ |
| T11: excepthook + screenshot | 1 módulo, 2 funções coesas | ✅ |
| T12: boot() + BootContext | 1 função orquestradora + 1 dataclass | ✅ |
| T13: CLI argparse | 1 módulo CLI | ✅ |
| T14: __main__.py + e2e | 3 linhas + 1 teste | ✅ |
| T15: README | 1 arquivo de doc | ✅ |
| T16: CHECKS.md + execução manual | 1 arquivo + 1 atividade | ✅ |

---

## Diagram-Definition Cross-Check

| Task | Depends On (body) | Diagram Shows | Status |
|---|---|---|---|
| T1 | — | (nó raiz) | ✅ |
| T2 | T1 | T1 → T2 | ✅ |
| T3 | T2 | T2 → T3 | ✅ |
| T4 | T2 | T2 → T4 [P] | ✅ |
| T5 | T2 | T2 → T5 [P] | ✅ |
| T6 | T2 | T2 → T6 [P] | ✅ |
| T7 | T5, T6 | (T5, T6) → T7 | ✅ |
| T8 | T5 | T5 → T8 (parte da trilha config) | ✅ |
| T9 | T2 | T2 → T9 [P] | ✅ |
| T10 | T9 | T9 → T10 | ✅ |
| T11 | T2, T10 | T10 → T11 (T2 já implícito via T10→T9→T2) | ✅ |
| T12 | T4, T7, T8, T10, T11 | (T4, T8, T11) → T12; T7 implícito via T8; T10 via T11 | ✅ |
| T13 | T12 | T12 → T13 | ✅ |
| T14 | T13 | T13 → T14 | ✅ |
| T15 | T14 | T14 → T15 [P] | ✅ |
| T16 | T14 | T14 → T16 [P] | ✅ |

**Parallelismo `[P]` validado:**
- Phase 2 (T4, T5, T6, T9): cada um cria arquivos diferentes, sem estado compartilhado, todos parallel-safe per matrix → ✅
- Phase 5 (T15, T16): arquivos diferentes (`README.md` vs `CHECKS.md`), zero overlap → ✅
- T10 e T11 NÃO são `[P]` mesmo que pudessem rodar em paralelo: ambos mexem em config global do structlog/sys.excepthook (parallel-safe: No na matrix) → ✅

---

## Test Co-location Validation

| Task | Code Layer | Matrix Requires | Task Says | Status |
|---|---|---|---|---|
| T1 | pyproject/lockfile | none | none | ✅ |
| T2 | estrutura/init.py | none | none | ✅ |
| T3 | tasks.py | none (manual) | none | ✅ |
| T4 | platform_info.py | unit | unit | ✅ |
| T5 | config/settings.py | unit | unit | ✅ |
| T6 | config/keyring_source.py | unit | unit | ✅ |
| T7 | config/settings.py (modify) + integração com keyring_source | integration (compõe layers) | integration | ✅ |
| T8 | config/display.py | unit | unit | ✅ |
| T9 | logger/processors.py | unit | unit | ✅ |
| T10 | logger/setup.py | integration | integration | ✅ |
| T11 | logger/screenshot_hook.py | integration | integration | ✅ |
| T12 | orchestrator/boot.py | integration | integration | ✅ |
| T13 | orchestrator/cli.py | unit | unit | ✅ |
| T14 | orchestrator/__main__.py | e2e | e2e | ✅ |
| T15 | README.md | none | none | ✅ |
| T16 | CHECKS.md + validação manual | none | none | ✅ |

Zero VIOLATIONS. Todos os layers que exigem teste têm o teste **co-located** na mesma task.

---

## Tool Allocation (resposta da ASK)

Como projeto é greenfield em ambiente Claude Code sem MCPs customizados configurados além de `context7`:

| Task | MCP | Skill | Razão |
|---|---|---|---|
| T1 | NONE | NONE | Setup mecânico |
| T2 | NONE | NONE | Setup mecânico |
| T3 | context7 (se houver dúvida em invoke) | NONE | API estável |
| T4 | NONE | NONE | stdlib apenas |
| T5 | context7 (pydantic-settings v2) | NONE | API recente |
| T6 | context7 (pydantic-settings v2 custom source) | NONE | API menos comum |
| T7 | NONE | NONE | Composição |
| T8 | NONE | NONE | Função simples |
| T9 | context7 (structlog processors) | NONE | Convenção structlog |
| T10 | context7 (structlog config) | NONE | API recente |
| T11 | NONE | NONE | stdlib + pyautogui simples |
| T12 | NONE | NONE | Composição |
| T13 | NONE | NONE | stdlib argparse |
| T14 | NONE | NONE | Trivial |
| T15 | NONE | NONE | Doc humana |
| T16 | NONE | NONE | Doc + execução manual |

---

## Requirement Coverage Final

| Requirement | Coberto por |
|---|---|
| M0-01 | T1 |
| M0-02 | T1 |
| M0-03 | T1 |
| M0-04 | T1 (wheels) + T9 (sanitização, parte de logging) |
| M0-05 | T13, T14 |
| M0-06 | T2 |
| M0-07 | T5, T6, T7 |
| M0-08 | T6, T7 |
| M0-09 | T5, T12 |
| M0-10 | T9, T10 |
| M0-11 | T8 |
| M0-12 | T7 |
| M0-13 | T10 |
| M0-14 | T10 |
| M0-15 | T11 |
| M0-16 | T10 |
| M0-17 | T9, T10 |
| M0-18 | T11 |
| M0-19 | T11 (mac vs win behavior) + T15 (docs de permissões) |
| M0-20 | T3 |
| M0-21 | T3 |
| M0-22 | T3 |
| M0-23 | T3 |
| M0-24 | T15 |
| M0-25 | T15 |
| M0-26 | T15 |

**Cobertura: 26/26 ✅**

---

## Pontos abertos / decisões pendentes (não-bloqueantes para começar)

1. **Sanitização não-recursiva** — `make_sanitizer` v1 não desce em dicts/listas nested. Documentar em STATE.md como limitação conhecida; melhorar quando aparecer caso real de log com payload nested sensível.
2. **Service name do keyring** = constante `"consigaz-robo"` (mesma para dev e prod). Se quisermos isolar, paramentrizar via `profile`. Adiar.
3. **Mensagem de erro exata para wheel ausente** — depende de mensagem do `uv`/`pip`. Vai ficar genérica até validarmos manualmente que ela é clara o suficiente.
