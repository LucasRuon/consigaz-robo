# Consigaz Robô — RPA Híbrido Cross-Platform

**Vision:** Robô RPA modular em Python que automatiza um aplicativo Desktop e uma plataforma Web interna da Consigaz, com camada de inteligência (LLM) para decisões sobre texto não-estruturado, rodando nativamente em macOS (Apple Silicon) e Windows.

**For:** Operação interna da Consigaz que hoje executa manualmente o ciclo "extrair dados do app local → validar/analisar → preencher formulário web".

**Solves:** Tempo gasto em digitação repetitiva, erros humanos de transferência de dados entre sistemas e ausência de classificação consistente de textos livres antes da próxima ação.

## Goals

- **Eficiência:** reduzir em ≥70% o tempo manual gasto no ciclo desktop→web (meta do PRD §2).
- **Confiabilidade:** zero erros de digitação/transferência em rotinas executadas em produção.
- **Portabilidade:** mesma base de código roda em macOS e Windows sem fork de lógica de negócio — apenas a camada `platform/` muda.
- **Manutenibilidade:** mudança de layout do app/web é corrigível alterando apenas arquivos de configuração (templates de imagem ou seletores DOM), sem tocar lógica.

## Tech Stack

**Core:**

- Linguagem: Python 3.11+
- Gerenciador de ambiente: `uv` (rápido, cross-platform, lockfile reproduzível) — alternativa: `venv + pip`
- Plataforma alvo: macOS (Apple Silicon arm64) + Windows (x86_64)

**Key dependencies:**

- `pyautogui` — controle de mouse/teclado (cross-platform)
- `opencv-python` — template matching para ancoragem visual
- `playwright` — automação web com seletores DOM
- `pandas` — validação estruturada e manipulação de dados
- `openai` — cliente oficial para a camada de inteligência (GPT-4/5)
- `keyring` — abstração para Keychain (macOS) e Credential Manager (Windows)
- `pygetwindow` / `pywin32` (Windows) / AppleScript via `subprocess` (macOS) — foco de janela
- `pydantic` + `pydantic-settings` — validação de config e variáveis de ambiente
- `tenacity` — retry com backoff exponencial (NFR do PRD)
- `pytest` — testes

## Scope

**v1 includes:**

- Orquestrador CLI que carrega config e despacha rotinas (`python -m orchestrator --routine X`)
- Módulo Desktop com camada de abstração `platform/{mac,win}` (foco de janela, atalhos, lançamento de app)
- Ancoragem visual via OpenCV com polling e timeout de 15s (sem `time.sleep` estático)
- Módulo Web com Playwright + sessão persistente (cookies/tokens reaproveitados)
- Camada de inteligência: validação determinística (Pandas) → OpenAI apenas para texto livre
- Gestão de credenciais via `keyring` (Keychain/Credential Manager) com fallback para `.env`
- Logging estruturado (`.log` + `.json`) + screenshots automáticos em falha
- Retry exponencial em toda chamada HTTP (web + LLM)
- **Uma rotina de automação end-to-end** demonstrando o happy path (rotina específica a ser definida na fase de spec)
- Suporte a agendamento via cron (macOS) e Task Scheduler (Windows) — documentado, não embutido

**Explicitly out of scope (v1):**

- UI gráfica para operadores (CLI only)
- Múltiplas máquinas executando em paralelo (single-host)
- Suporte a Linux
- Múltiplos provedores de LLM (só OpenAI; abstração pode vir depois)
- Bypass de CAPTCHAs (mitigação é usar sessão persistente para evitá-los)
- Distribuição como executável empacotado (.dmg/.exe) — usuário roda via Python

## Constraints

- **Técnico:** Toda dependência precisa ter wheel pré-compilada para `arm64-darwin` E `win-amd64`. Bibliotecas que exigem compilação a partir do source são vetadas.
- **Técnico:** Templates de imagem (`assets/templates/`) podem precisar de variantes por SO porque a renderização nativa difere — a fase de design vai validar se uma pasta única com tolerância maior funciona ou se precisa de `assets/templates/{darwin,win32}/`.
- **Técnico:** Nenhum segredo em código ou em logs (NFR-5.4 do PRD).
- **Operacional:** Robô roda agendado em **uma máquina dedicada** por vez (não há sincronização entre instâncias).
- **Pendente de definição (não bloqueante para M0):**
  - Nome/identificador do aplicativo Desktop alvo (precisa para `open -a` no macOS e caminho do `.exe` no Windows)
  - URL e fluxo da plataforma web interna da Consigaz
  - Qual rotina específica será o caso de uso da v1
