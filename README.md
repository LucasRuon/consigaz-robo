# Consigaz Robô

Robô RPA híbrido (Desktop + Web) cross-platform para macOS e Windows, com camada de inteligência via LLM.

## Visão geral

O Consigaz Robô automatiza fluxos de trabalho que dependem tanto de um aplicativo desktop legado quanto de portais web modernos. A automação acontece em três camadas coordenadas pelo orquestrador: um módulo desktop que dirige o app local por meio de PyAutoGUI e template matching com OpenCV (sem coordenadas fixas), um módulo web baseado em Playwright que injeta dados em formulários multi-etapas com seletores DOM robustos, e uma camada de inteligência que valida dados estruturados com Pandas e delega texto livre a uma LLM (OpenAI/Anthropic) para classificação e análise semântica.

O problema resolvido é o retrabalho manual entre sistemas heterogêneos: hoje um operador precisa abrir o app desktop, extrair informações, julgar texto não estruturado e, em seguida, replicar o resultado em formulários web. O robô elimina essas etapas, mantendo um ponto único de configuração para credenciais, logs estruturados com sanitização automática de segredos e uma esteira de qualidade (`ruff`, `mypy --strict`, `pytest`) que garante regressões cobertas.

A separação modular é uma exigência do projeto, não uma sugestão. Mudanças de layout do sistema-alvo devem ser corrigíveis ajustando templates de imagem ou seletores em arquivos de configuração isolados, sem mexer na lógica de negócio.

## Pré-requisitos

- **Python 3.11 ou superior** (recomendado 3.12 ou 3.13; suportamos até 3.14)
- **`uv`** para gestão de ambiente e dependências
- **`git`** para clone do repositório
- **macOS** (Apple Silicon ou Intel) ou **Windows 10/11**

## Instalação no macOS

### 1. Instalar Python 3.11+

Opção A — via `pyenv` (recomendada para múltiplas versões):

```bash
brew install pyenv
pyenv install 3.13
pyenv global 3.13
```

Opção B — installer oficial: baixe em <https://www.python.org/downloads/macos/> e execute o `.pkg`.

### 2. Instalar `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reabra o terminal ou rode `source $HOME/.local/bin/env` (ou equivalente segundo o instalador) para carregar o `uv` no `PATH`.

### 3. Clonar e sincronizar dependências

```bash
git clone <repo-url> consigaz-robo
cd consigaz-robo
uv sync --extra dev
```

### 4. Permissões macOS críticas

Abra **System Settings → Privacy & Security** e conceda ao seu terminal (Terminal.app, iTerm, Warp, VS Code, etc.):

- **Acessibilidade** — obrigatório para o PyAutoGUI controlar mouse e teclado.
- **Gravação de Tela** — obrigatório para o OpenCV fazer template matching em screenshots e para o `screenshot_hook` capturar imagens de erro.

Sem essas duas permissões o módulo desktop falha silenciosamente em qualquer rotina real.

### 5. Validar instalação

```bash
uv run inv test
uv run python -m orchestrator --help
```

A suíte deve retornar verde (72 testes passando atualmente) e o `--help` deve imprimir o banner do orquestrador.

## Instalação no Windows

### 1. Instalar Python 3.11+

Baixe o instalador em <https://www.python.org/downloads/windows/> e, durante a instalação, **marque a opção "Add Python to PATH"**. Confirme no PowerShell:

```powershell
python --version
```

### 2. Instalar `uv`

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Feche e reabra o PowerShell para garantir que o `uv` foi adicionado ao `PATH`.

### 3. Clonar e sincronizar dependências

```powershell
git clone <repo-url> consigaz-robo
cd consigaz-robo
uv sync --extra dev
```

### 4. Notas de execução

- O **UAC** pode pedir aprovação na primeira execução que dispare automação de UI; aprove uma vez.
- Rode o orquestrador com o **usuário normal**, não como administrador — o PyAutoGUI não interage com janelas elevadas a partir de um processo não elevado.
- Garanta o terminal em UTF-8 (ver Troubleshooting) para evitar mojibake em logs.

### 5. Validar instalação

```powershell
uv run inv test
uv run python -m orchestrator --help
```

## Configuração de segredos

A `Settings` resolve segredos nesta ordem de precedência:

1. **Keyring nativo do SO** (Keychain no macOS, Credential Manager no Windows) — recomendado para produção.
2. **Arquivo `.env`** na raiz do projeto — útil para desenvolvimento local.
3. **Variáveis de ambiente** do shell.

### Gravar segredos no keyring

**macOS (Keychain):**

```bash
security add-generic-password -s consigaz-robo -a openai_api_key -w 'sk-...'
security add-generic-password -s consigaz-robo -a desktop_app_password -w '...'
security add-generic-password -s consigaz-robo -a web_platform_password -w '...'
```

**Windows (Credential Manager):**

```powershell
cmdkey /generic:consigaz-robo /user:openai_api_key /pass:sk-...
cmdkey /generic:consigaz-robo /user:desktop_app_password /pass:...
cmdkey /generic:consigaz-robo /user:web_platform_password /pass:...
```

### Alternativa local (apenas desenvolvimento)

Copie o template e preencha os valores:

```bash
cp .env.example .env
```

**Nunca commite `.env`** — o arquivo já está listado no `.gitignore`. Em `PROFILE=prod` o boot falha caso algum segredo obrigatório esteja ausente.

## Comandos comuns

Todos os comandos abaixo rodam dentro do ambiente isolado pelo `uv`. Use `uv run inv <task>` para tasks do invoke e `uv run python -m orchestrator` para a CLI.

| Comando | Descrição |
| --- | --- |
| `uv run inv setup` | Sincroniza dependências runtime + dev (`uv sync --extra dev`) |
| `uv run inv test` | Roda a suíte `pytest` completa |
| `uv run inv test --only tests/test_x.py` | Roda apenas um arquivo ou caminho de teste |
| `uv run inv lint` | `ruff check` em `src/` e `tests/` |
| `uv run inv format` | `ruff format` em `src/` e `tests/` |
| `uv run inv typecheck` | `mypy --strict` em `src/` |
| `uv run inv smoke` | Smoke e2e: executa `python -m orchestrator --help` |
| `uv run inv clean` | Remove caches (`.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `__pycache__`) |
| `uv run python -m orchestrator --help` | Mostra ajuda da CLI |
| `uv run python -m orchestrator --routine NOME` | Executa uma rotina específica (despacho real chega em M4) |
| `uv run python -m orchestrator --dry-run` | Executa o boot sem efeitos colaterais |

## Estrutura do projeto

```
consigaz-robo/
├── src/
│   ├── orchestrator/        # CLI + boot: ponto de entrada, mapeia exceções para exit codes
│   ├── config/              # Settings (Pydantic), KeyringSource e display de configuração
│   ├── logger/              # Setup dual sink (console + arquivo), processors com sanitizer e screenshot_hook
│   └── platform_info/       # Detecção de SO e capacidades nativas
├── tests/                   # Suíte pytest (espelha layout de src/)
├── assets/
│   └── templates/           # Imagens-âncora para template matching (OpenCV) por tela
├── logs/
│   └── errors/              # Screenshots e logs de falha (<timestamp>_<rotina>.png/.log)
├── .specs/project/          # PROJECT.md, ROADMAP.md, STATE.md
├── tasks.py                 # Definições do invoke (setup/test/lint/format/typecheck/smoke/clean)
├── pyproject.toml           # Metadados do projeto, deps e configuração de ferramentas
├── uv.lock                  # Lockfile do uv
├── .env.example             # Template de segredos para desenvolvimento local
├── prd_automacao_rpa.md     # PRD original
└── CLAUDE.md                # Instruções para o assistente Claude Code
```

As fronteiras importam: o módulo desktop nunca importa o web, o módulo web não tem nenhuma dependência visual, e a decisão condicional (aprovado → web, reprovado → exceção) vive na camada de inteligência, nunca dentro de um módulo de UI.

## Troubleshooting

### `uv sync` falha com mensagem "no wheel for arch"

Alguma dependência nativa (geralmente `opencv-python` ou `numpy`) ainda não publicou wheel para a versão do Python escolhida. Force uma versão LTS amplamente suportada:

```bash
uv python install 3.13
uv python pin 3.13
uv sync --extra dev
```

### macOS: `pyautogui` não move o mouse nem digita

Falta a permissão **Acessibilidade**. Vá em **System Settings → Privacy & Security → Accessibility**, adicione o terminal (Terminal.app, iTerm, Warp, VS Code, etc.) e marque o toggle. Pode ser necessário reiniciar o terminal.

### macOS: screenshot de erro fica preto ou vazio

Falta a permissão **Gravação de Tela**. Vá em **System Settings → Privacy & Security → Screen Recording**, adicione o terminal e reabra a sessão. Sem essa permissão o `screenshot_hook` captura uma imagem em branco e o template matching nunca encontra âncoras.

### Windows: caracteres mojibake (`Ã§`, `Ã£`) no log do terminal

Os arquivos do projeto já são UTF-8. O problema é o code page do console. Antes de rodar o orquestrador:

```powershell
chcp 65001
```

Para tornar persistente, configure o perfil do PowerShell ou ative "Use Unicode UTF-8 for worldwide language support" em **Configurações do Windows → Hora e Idioma → Idioma → Configurações administrativas de idioma**.

### `ModuleNotFoundError: No module named 'orchestrator'`

A invocação ignorou o ambiente do `uv`. Rode sempre via `uv run`:

```bash
uv run python -m orchestrator --help
```

Chamar `python -m orchestrator` diretamente só funciona com o `.venv` previamente ativado.

### `uv run inv ...` reclama que `invoke` não está instalado

A sincronização não incluiu o grupo de desenvolvimento. Rode novamente com a extra:

```bash
uv sync --extra dev
```

## Links para mais detalhes

- `.specs/project/PROJECT.md` — visão de produto, escopo e decisões arquiteturais
- `.specs/project/ROADMAP.md` — milestones e fases planejadas
- `prd_automacao_rpa.md` — PRD original do robô RPA
- `CLAUDE.md` — instruções para o assistente Claude Code (regras invariantes e convenções)
