# M0 — Fundação Cross-Platform Specification

## Problem Statement

O projeto é greenfield: existe só o PRD. Sem estrutura, sem dependências, sem logging, sem segredos gerenciados, qualquer trabalho subsequente (Desktop, Web, Inteligência) ficaria bloqueado ou seria construído sobre ar. Antes de implementar qualquer rotina de automação, precisamos de uma fundação **comprovadamente cross-platform** (macOS arm64 + Windows x86_64) que respeite as restrições invariantes do projeto.

## Goals

- [ ] Desenvolvedor consegue clonar o repo e executar `make setup` (ou equivalente) em macOS OU Windows e ter ambiente funcional em ≤5min
- [ ] `python -m orchestrator --help` imprime sem erro em ambos SOs (smoke test)
- [ ] Logs estruturados gravam em `.log` (humano) E `.json` (estruturado) com sanitização de campos sensíveis
- [ ] Credenciais resolvem via Keychain (mac) / Credential Manager (win) com fallback transparente para `.env`
- [ ] Nenhuma dependência exige compilação a partir do source nos dois SOs (todas têm wheel)

## Out of Scope

| Feature | Reason |
|---|---|
| Adapter de plataforma desktop (mac/win) | Pertence a M1 — aqui só validamos que as bibliotecas instalam |
| Cliente Playwright | Pertence a M2 |
| Cliente OpenAI | Pertence a M3 |
| Rotinas de automação reais | Pertence a M5 |
| CI/CD em nuvem (GitHub Actions, etc.) | Validação cross-platform é manual nas duas máquinas na v1 |
| Empacotamento (.dmg, .exe, PyInstaller) | Out of scope do projeto inteiro v1 |
| Linux | Out of scope do projeto v1 |
| Docker | RPA precisa de UI nativa — não faz sentido conteinerizar |

---

## User Stories

### P1: Setup do projeto cross-platform ⭐ MVP

**User Story**: Como desenvolvedor que vai implementar M1–M5, quero clonar o repo e ter ambiente funcional em macOS ou Windows com um único comando, para começar a codar sem perder horas com setup ambiente.

**Why P1**: Sem isto, ninguém consegue rodar nada. Bloqueia todos os outros milestones.

**Acceptance Criteria**:

1. WHEN o desenvolvedor executa o comando de setup em macOS arm64 com Python 3.11+ instalado THEN o sistema SHALL criar ambiente virtual, instalar dependências e finalizar em ≤5min sem erros
2. WHEN o desenvolvedor executa o mesmo comando em Windows 10/11 x86_64 com Python 3.11+ instalado THEN o sistema SHALL produzir resultado equivalente (mesmas deps, mesmo lockfile resolvido)
3. WHEN o setup termina THEN o sistema SHALL conseguir importar `cv2`, `pyautogui`, `pandas`, `keyring`, `pydantic`, `tenacity`, `openai` sem ImportError
4. WHEN alguma dependência não tem wheel para o SO/arch atual THEN o sistema SHALL falhar **explicitamente** no setup (não silenciosamente compilar do source)
5. WHEN o desenvolvedor executa `python -m orchestrator --help` após setup THEN o sistema SHALL imprimir mensagem de uso e retornar exit code 0
6. WHEN o projeto é inicializado THEN a estrutura de diretórios SHALL conter `orchestrator/`, `desktop/`, `web/`, `intelligence/`, `config/`, `assets/templates/`, `logs/errors/`, `tests/` conforme PRD §3

**Independent Test**: Em uma máquina limpa de cada SO, clonar, rodar setup, rodar `python -m orchestrator --help`, verificar exit code e saída.

---

### P1: Configuração e gerenciamento de segredos ⭐ MVP

**User Story**: Como operador do robô, quero que credenciais (OpenAI API key, senha do app desktop, senha da plataforma web) sejam carregadas de cofre nativo do SO ou `.env`, para nunca expor segredos em código ou logs.

**Why P1**: NFR-5.4 do PRD é invariante. Sem isto, qualquer integração subsequente vira risco de segurança.

**Acceptance Criteria**:

1. WHEN o orquestrador inicia THEN o sistema SHALL resolver segredos via `keyring` (Keychain no macOS, Credential Manager no Windows)
2. WHEN um segredo não existe no keyring THEN o sistema SHALL fazer fallback para `.env` na raiz do projeto
3. WHEN um segredo não existe nem no keyring nem no `.env` E é marcado como obrigatório THEN o sistema SHALL falhar na inicialização com mensagem clara identificando qual segredo falta (sem vazar valores)
4. WHEN o sistema loga qualquer evento THEN nenhum segredo SHALL aparecer no log (validado por teste que tenta logar um segredo conhecido e verifica que ele foi mascarado)
5. WHEN o desenvolvedor consulta a configuração via `config.show()` (utilitário CLI) THEN segredos SHALL aparecer mascarados (ex: `sk-***`)
6. WHEN `.env` existe E contém um segredo THEN ele SHALL ter precedência menor que o keyring (keyring vence se ambos estiverem definidos)

**Independent Test**: Setar `OPENAI_API_KEY=sk-test123` no `.env`, rodar `python -c "from config import settings; print(settings.openai_api_key.get_secret_value())"`, verificar valor. Depois setar o mesmo no keyring com valor diferente, rodar novamente, verificar que valor do keyring vence. Tentar logar o segredo — verificar que aparece mascarado.

---

### P1: Logging estruturado dual com captura de erro ⭐ MVP

**User Story**: Como operador depurando uma falha em execução agendada, quero logs legíveis E logs JSON estruturados, com screenshot automático em erros, para entender o que aconteceu sem precisar reproduzir.

**Why P1**: FR-1.3 do PRD. Toda execução agendada que falha precisa deixar evidência forense suficiente.

**Acceptance Criteria**:

1. WHEN o orquestrador inicia uma execução THEN o sistema SHALL criar dois arquivos: `logs/<timestamp>_<rotina>.log` (texto humano) e `logs/<timestamp>_<rotina>.json` (estruturado, uma linha JSON por evento)
2. WHEN qualquer módulo loga via logger central THEN o evento SHALL aparecer em **ambos** os arquivos
3. WHEN uma exceção não tratada chega ao orquestrador THEN o sistema SHALL capturar screenshot da tela inteira E salvar em `logs/errors/<timestamp>_<rotina>.png`
4. WHEN o screenshot é capturado E a captura em si falha (ex: sem permissão) THEN o sistema SHALL registrar o erro de captura no log mas NÃO SHALL mascarar a exceção original
5. WHEN um campo conhecido como sensível (lista configurável: `password`, `api_key`, `token`, `secret`, `cpf`, `cnpj`) aparece em qualquer registro de log THEN o valor SHALL ser substituído por `***`
6. WHEN o nível de log é configurado via env (`LOG_LEVEL=DEBUG`) THEN o sistema SHALL respeitar o nível em ambos os arquivos
7. WHEN o sistema roda em macOS THEN a captura de screenshot SHALL funcionar com permissão de "Gravação de Tela" concedida (documentar como conceder); WHEN roda em Windows THEN SHALL funcionar sem permissão extra

**Independent Test**: Rodar um script que loga eventos de cada nível, lança uma exceção customizada e tenta logar um dict com `password=segredo`. Verificar: dois arquivos criados, screenshot na pasta de erros, segredo mascarado nos dois arquivos.

---

### P2: Tooling de desenvolvimento (lint, type-check, test runner)

**User Story**: Como desenvolvedor, quero `make lint`, `make test`, `make typecheck` funcionando idênticos em mac e win, para feedback rápido sobre qualidade do código.

**Why P2**: Acelera desenvolvimento mas não bloqueia funcionalidade. Pode entrar paralelo com M1.

**Acceptance Criteria**:

1. WHEN o desenvolvedor executa `make lint` (ou `python -m task lint`) THEN o sistema SHALL rodar `ruff check` e retornar exit code 0 se não houver violações
2. WHEN o desenvolvedor executa `make test` THEN o sistema SHALL rodar `pytest` com cobertura básica e retornar resultado
3. WHEN o desenvolvedor executa `make typecheck` THEN o sistema SHALL rodar `mypy` (ou `pyright`) em modo strict para os módulos definidos
4. WHEN qualquer dos comandos roda em Windows THEN o sistema SHALL produzir saída equivalente (sem dependência de `make` nativo — usar `invoke` ou `tasks.py` cross-platform)

**Independent Test**: Em cada SO, rodar os três comandos em um repo limpo e verificar que terminam sem erro.

---

### P3: Documentação de instalação por SO

**User Story**: Como novo desenvolvedor do projeto, quero um README claro com passos de instalação separados por SO, para não tropeçar em peculiaridades (permissões macOS, Python no PATH no Windows).

**Why P3**: Importante mas pode ser refinado iterativamente.

**Acceptance Criteria**:

1. WHEN um novo desenvolvedor lê o README THEN ele SHALL encontrar seções separadas e completas para macOS e Windows
2. WHEN a seção macOS é seguida THEN ela SHALL incluir: instalação Python 3.11+, instalação `uv`, comando de setup, e instruções para conceder Acessibilidade e Gravação de Tela ao terminal/iTerm
3. WHEN a seção Windows é seguida THEN ela SHALL incluir: instalação Python 3.11+ (com PATH), instalação `uv`, comando de setup, e nota sobre UAC se aplicável

---

## Edge Cases

- WHEN Python instalado é <3.11 THEN o sistema SHALL detectar no setup e falhar com mensagem clara
- WHEN o desenvolvedor está em macOS Intel (x86_64) em vez de Apple Silicon THEN o sistema SHALL funcionar (não é arquitetura alvo otimizada, mas wheels universal2 cobrem)
- WHEN o desenvolvedor está em Windows ARM64 THEN o sistema PODE falhar (não é arquitetura suportada na v1, documentar)
- WHEN `logs/` ou `logs/errors/` não existe no primeiro run THEN o sistema SHALL criá-las automaticamente
- WHEN o disco está cheio E o logger tenta gravar THEN o sistema SHALL falhar de forma controlada (não corromper estado)
- WHEN o `.env` tem sintaxe inválida THEN o sistema SHALL falhar na inicialização com a linha problemática identificada
- WHEN `keyring` não está disponível (ex: macOS sem GUI logado) THEN o sistema SHALL cair para `.env` sem warning ruidoso

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|---|---|---|---|
| M0-01 | P1 Setup | Tasks | Pending |
| M0-02 | P1 Setup | Tasks | Pending |
| M0-03 | P1 Setup | Tasks | Pending |
| M0-04 | P1 Setup | Tasks | Pending |
| M0-05 | P1 Setup | Tasks | Pending |
| M0-06 | P1 Setup | Tasks | Pending |
| M0-07 | P1 Secrets | Tasks | Pending |
| M0-08 | P1 Secrets | Tasks | Pending |
| M0-09 | P1 Secrets | Tasks | Pending |
| M0-10 | P1 Secrets | Tasks | Pending |
| M0-11 | P1 Secrets | Tasks | Pending |
| M0-12 | P1 Secrets | Tasks | Pending |
| M0-13 | P1 Logging | Tasks | Pending |
| M0-14 | P1 Logging | Tasks | Pending |
| M0-15 | P1 Logging | Tasks | Pending |
| M0-16 | P1 Logging | Tasks | Pending |
| M0-17 | P1 Logging | Tasks | Pending |
| M0-18 | P1 Logging | Tasks | Pending |
| M0-19 | P1 Logging | Tasks | Pending |
| M0-20 | P2 Tooling | Tasks | Pending |
| M0-21 | P2 Tooling | Tasks | Pending |
| M0-22 | P2 Tooling | Tasks | Pending |
| M0-23 | P2 Tooling | Tasks | Pending |
| M0-24 | P3 Docs | Tasks | Pending |
| M0-25 | P3 Docs | Tasks | Pending |
| M0-26 | P3 Docs | Tasks | Pending |

**Coverage:** 26 total, 0 mapped to tasks (Tasks phase ainda não rodou).

---

## Success Criteria

- [ ] Em uma máquina macOS arm64 limpa: clone → setup → `python -m orchestrator --help` funciona em ≤5min
- [ ] Em uma máquina Windows 10/11 x86_64 limpa: mesmo resultado em ≤5min
- [ ] Teste de segredos: keyring vence `.env`, segredo nunca aparece em log, falta de segredo obrigatório bloqueia start
- [ ] Teste de logging: dois arquivos criados, screenshot em exceção, sanitização funcionando
- [ ] Suite `pytest` roda verde em ambos SOs com cobertura ≥80% nos módulos de M0 (`config`, `logger`)
