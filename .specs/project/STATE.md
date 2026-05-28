# State

Memória persistente entre sessões: decisões, blockers, lições, todos, ideias adiadas.

---

## Decisions

### 2026-05-28 — Suporte cross-platform (macOS + Windows)
O PRD foi escrito para macOS Apple Silicon apenas. Decisão: estender para Windows desde a v1, via camada de abstração `desktop/platform/{mac,win}.py`. A lógica de negócio (orquestrador, web, inteligência) permanece única; apenas foco de janela, atalhos modificadores e launcher de app variam por SO.
**Implicação:** Toda dependência precisa de wheel pré-compilada para `arm64-darwin` E `win-amd64`. Bibliotecas que compilam do source são vetadas.

### 2026-05-28 — LLM = OpenAI (GPT-4/5)
Provedor único na v1. Sem abstração multi-LLM por ora (YAGNI). Prompts ficam versionados em `config/prompts/` para troca futura sem refatoração de código.

### 2026-05-28 — Execução: agendada em uma máquina dedicada
Single-host. Sem coordenação multi-instância na v1. Agendamento documentado via cron (macOS) e Task Scheduler (Windows), não embutido no código.

### 2026-05-28 — Gerenciador de ambiente: `uv`
Mais rápido que `pip`, lockfile reproduzível, funciona idêntico em macOS e Windows. `venv + pip` fica como fallback documentado se houver resistência.

---

## Blockers

### Bloqueador de M5 — Identificação do app desktop alvo
Precisamos do nome/bundle ID do app no macOS (`open -a "Nome do App"`) e do caminho do executável no Windows. Sem isso, não dá pra implementar a primeira rotina end-to-end.

### Bloqueador de M5 — Plataforma web interna da Consigaz
Precisamos da URL base, fluxo de login (form/SSO), e mapa dos formulários alvo. Sem isso, módulo Web fica genérico demais.

### Bloqueador de M5 — Definição da rotina-piloto
Qual processo manual exato será automatizado primeiro? Sem isso, não dá pra escrever spec, capturar templates ou mapear seletores.

---

## TODOs

- Confirmar com o usuário: `uv` ou `venv + pip`?
- Antes de M1: decidir se templates de imagem ficam em pasta única (`assets/templates/`) ou separados por SO (`assets/templates/darwin/`, `assets/templates/win32/`). Validar empiricamente no primeiro template real.
- Antes de M2: definir convenção de nomenclatura para `selectors.json` (por página? por feature?).

---

## Deferred Ideas

- Abstração multi-LLM (Anthropic, modelos locais) — fora do escopo v1; reavaliar após M5.
- Empacotamento como executável (.dmg/.exe) — usuário roda via Python por ora.
- Dashboard web lendo os `.json` logs — boa ideia para milestone futura.
- Modo "atendido" com confirmação humana em decisões de baixa confiança da LLM.

---

## Lessons

(Vazio — será preenchido conforme o projeto evoluir.)

---

## Preferences

- Idioma: Português (PT-BR) para toda comunicação e documentação interna.
- Estilo de commits: a definir na fase de setup (sugestão: Conventional Commits).
