# Implantação no Cliente + Configuração TOTVS

Runbook operacional para colocar o **consigaz-robo** rodando na máquina do
cliente, integrado ao **TOTVS desktop**, do zero até execução agendada em
produção. Este documento é o guia que o técnico de campo (ou engenheiro
remoto) segue passo a passo durante a visita / sessão de implantação.

Pré-leituras recomendadas:

- `README.md` — visão geral, instalação e troubleshooting cross-platform.
- `CLAUDE.md` — regras invariantes (sem coordenadas hardcoded, timeout 15s,
  template matching obrigatório no desktop).
- `docs/scheduling.md` — receitas de agendamento (Task Scheduler / cron).
- `prd_automacao_rpa.md` — PRD original.

> **Convenção:** todo bloco `powershell` neste guia é executado no PowerShell
> do **usuário operacional** do cliente (NÃO administrador). Todo bloco `bash`
> é referência para sua máquina de desenvolvimento (macOS).

---

## Sumário

1. [Modelo de implantação](#1-modelo-de-implantação)
2. [Pré-requisitos da máquina do cliente](#2-pré-requisitos-da-máquina-do-cliente)
3. [Roteiro de implantação (Fase 1 — instalar)](#3-roteiro-de-implantação-fase-1--instalar)
4. [Configuração de credenciais](#4-configuração-de-credenciais)
5. [Mapeamento do TOTVS (Fase 2 — captura assistida)](#5-mapeamento-do-totvs-fase-2--captura-assistida)
6. [Estrutura de templates e seletores para TOTVS](#6-estrutura-de-templates-e-seletores-para-totvs)
7. [Criação da rotina TOTVS](#7-criação-da-rotina-totvs)
8. [Validação no cliente (Fase 3 — testar)](#8-validação-no-cliente-fase-3--testar)
9. [Agendamento e disparo](#9-agendamento-e-disparo)
10. [Operação, logs e suporte](#10-operação-logs-e-suporte)
11. [Atualizações e versionamento](#11-atualizações-e-versionamento)
12. [Troubleshooting de campo](#12-troubleshooting-de-campo)
13. [Checklist final de aceite](#13-checklist-final-de-aceite)
14. [Anexos](#14-anexos)

---

## 1. Modelo de implantação

### 1.1 Por que rodar local no Windows do cliente

O robô precisa estar **na mesma máquina onde o TOTVS desktop roda hoje**. O
módulo desktop usa template matching com OpenCV em screenshots reais — isso
exige:

- Janela do TOTVS **visível** na tela primária (mesmo monitor, mesma
  resolução, mesmo DPI, mesmo tema do operador).
- Driver de mouse/teclado nativo (PyAutoGUI envia eventos do sistema).
- Acesso aos arquivos de log locais (pasta `logs/`).

Por isso evitamos:

| Opção                                   | Por que **não**                                                                 |
| --------------------------------------- | ------------------------------------------------------------------------------- |
| RPA rodando no servidor + RDP no TOTVS  | O RDP escala/comprime a imagem; templates pixel-exatos quebram.                 |
| RPA no Mac do desenvolvedor             | TOTVS não roda em macOS, e templates capturados em outra máquina não casam.     |
| RPA em VM no servidor sem sessão ativa  | PyAutoGUI exige sessão interativa logada; sessão bloqueada → screenshot preto.  |
| RPA como Serviço Windows (Session 0)    | Session 0 não tem desktop interativo — automação de UI **não funciona** ali.    |

**Decisão:** o robô é instalado como aplicação de usuário na estação de
trabalho do operador, executado pelo Task Scheduler com a sessão do usuário
**desbloqueada** (ou sob auto-logon dedicado — ver §9).

### 1.2 Topologia

```
┌─────────────────────────────────────────────────────────────┐
│  Estação de trabalho Windows do cliente                      │
│                                                              │
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────┐ │
│  │ TOTVS        │◄───┤ consigaz-robo    │───►│ Navegador  │ │
│  │ desktop      │    │ (Python + uv)    │    │ Playwright │ │
│  └──────────────┘    └────────┬─────────┘    └────────────┘ │
│         ▲                     │                              │
│         │                     ▼                              │
│   template match     ┌─────────────────┐                     │
│   (OpenCV)           │ Credential      │                     │
│                      │ Manager (segre.)│                     │
│                      └─────────────────┘                     │
│                              │                               │
│                              ▼                               │
│                      ┌─────────────────┐                     │
│                      │ logs/ (local)   │                     │
│                      └─────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
              │
              ▼ (HTTPS)
       ┌──────────────┐
       │ LLM provider │ (OpenAI / Anthropic)
       └──────────────┘
```

### 1.3 Fases da implantação

```
┌─────────────┐   ┌──────────────────┐   ┌──────────────┐   ┌────────────┐
│ Fase 1      │ → │ Fase 2           │ → │ Fase 3       │ → │ Fase 4     │
│ Instalar    │   │ Mapear TOTVS     │   │ Validar      │   │ Agendar    │
│ (~1 h)      │   │ (1-2 dias)       │   │ (meio dia)   │   │ (1 h)      │
└─────────────┘   └──────────────────┘   └──────────────┘   └────────────┘
```

Fase 1 e Fase 4 são repetíveis em qualquer cliente — quase scriptáveis.
Fase 2 é o trabalho real e **precisa ser feito presencialmente (ou via sessão
remota assistida com o operador na linha)** porque cada TOTVS é visualmente
único (versão, módulos contratados, customizações, tema, resolução).

---

## 2. Pré-requisitos da máquina do cliente

### 2.1 Hardware mínimo

- CPU x86_64 (qualquer Intel/AMD moderno).
- RAM: 8 GB (16 GB recomendado se rodar concorrente com TOTVS pesado).
- Disco: ~3 GB livres (Python + Playwright Chromium + logs).
- Monitor primário em **resolução nativa fixa** (não alterar zoom de tela
  depois de capturar os templates).

### 2.2 Software

- **Windows 10 21H2+ ou Windows 11**.
- **Python 3.11 ou superior** (recomendado 3.13).
- **`uv`** (gerenciador de ambiente).
- **`git`** opcional (para `git pull` em updates; pode-se também receber zip).
- **TOTVS desktop** já instalado, funcional, com login válido para o usuário
  operacional.
- Conta de usuário Windows **dedicada** para a automação (recomendado),
  separada da conta administrativa. Veja §2.4.

### 2.3 Rede

- Saída HTTPS liberada para:
  - `api.openai.com` (ou `api.anthropic.com`, conforme provider escolhido).
  - Domínios do **portal web Consigaz** que o robô usará (mesmos do operador
    humano hoje).
  - `playwright.azureedge.net` no momento do `playwright install chromium`
    (pode ser uma única vez; depois funciona offline).
- Sem proxy MITM que reescreva certificados — se houver, importar a CA
  corporativa no `certifi` do venv (ver §12).

### 2.4 Conta de usuário recomendada

Crie um usuário Windows dedicado, ex.: `consigaz-rpa`:

- Não administrador.
- Senha forte armazenada no cofre da empresa.
- Auto-logon configurado **se** a máquina ficar dedicada ao robô (ver §9.3).
- Política de bloqueio de tela **desativada** ou com timeout maior que o
  intervalo de execução (caso contrário a tela bloqueia → PyAutoGUI falha).

### 2.5 Permissões / UAC

- O UAC pode pedir aprovação na primeira execução que dispare automação de
  UI. **Aprovar uma vez** e marcar para lembrar.
- Não rodar o robô como **Administrador**: PyAutoGUI não consegue clicar em
  janelas elevadas a partir de um processo não-elevado, e vice-versa. Mantenha
  TODOS os processos no mesmo nível (preferência: usuário normal).

---

## 3. Roteiro de implantação (Fase 1 — instalar)

Tempo estimado: **45–90 min**. Pode ser executado por técnico de TI do
cliente seguindo este script.

### 3.1 Instalar Python 3.13

1. Abrir <https://www.python.org/downloads/windows/> e baixar o **Windows
   installer (64-bit)** da última 3.13.x.
2. Executar o instalador.
3. **Marcar "Add python.exe to PATH"** na primeira tela.
4. Clicar em "Install Now".
5. Validar no PowerShell:

   ```powershell
   python --version
   ```

   Saída esperada: `Python 3.13.x`.

### 3.2 Instalar `uv`

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Fechar e reabrir o PowerShell. Validar:

```powershell
uv --version
```

### 3.3 Obter o código

**Opção A — git (recomendado, simplifica updates):**

```powershell
cd C:\
git clone <repo-url> consigaz-robo
cd consigaz-robo
```

**Opção B — pacote zip (quando não há git no cliente):**

1. Você (dev) gera o zip:
   ```bash
   git archive --format=zip --output=consigaz-robo-vX.Y.Z.zip HEAD
   ```
2. Operador extrai em `C:\consigaz-robo\`.

### 3.4 Sincronizar dependências

```powershell
cd C:\consigaz-robo
uv sync
```

> **Nota:** não usar `--extra dev` em produção. As ferramentas de
> desenvolvimento (`pytest`, `ruff`, `mypy`) não são necessárias no cliente.

### 3.5 Instalar o navegador do Playwright

```powershell
uv run playwright install chromium
```

Isso baixa ~150 MB. Em redes corporativas com proxy, ver §12.

### 3.6 Garantir UTF-8 no console

Adicionar ao perfil do PowerShell do usuário operacional (ou rodar antes de
cada sessão):

```powershell
chcp 65001
```

Para tornar permanente em todo o SO, ativar em **Configurações do Windows →
Hora e Idioma → Idioma → Configurações administrativas de idioma → Beta: Use
Unicode UTF-8**.

### 3.7 Criar estrutura de logs

Já é criada automaticamente pelo orquestrador na primeira execução, mas
podemos pré-criar para validar permissões de escrita:

```powershell
mkdir C:\consigaz-robo\logs\errors -Force
```

### 3.8 Smoke test inicial (sem rotina real)

```powershell
cd C:\consigaz-robo
uv run python -m orchestrator --help
uv run python -m orchestrator --list
```

A primeira impressão do banner e a listagem de rotinas (mesmo que liste
apenas `pilot-smoke`) confirmam que o ambiente está sadio. Se isso passar,
**Fase 1 está concluída**.

---

## 4. Configuração de credenciais

> **Regra invariante (CLAUDE.md):** credenciais **nunca** em código, nunca em
> repositório, nunca em logs. Em `PROFILE=prod` o boot **falha** se algum
> segredo obrigatório estiver ausente.

A `Settings` resolve segredos nesta ordem:

1. **Credential Manager do Windows** (cofre nativo) — **usar em produção**.
2. Arquivo `.env` na raiz — apenas para desenvolvimento.
3. Variáveis de ambiente do shell.

### 4.1 Gravar segredos no Credential Manager

Executar **como o usuário operacional** (não admin):

```powershell
# Provedor de LLM
cmdkey /generic:consigaz-robo /user:openai_api_key /pass:sk-...

# Login TOTVS
cmdkey /generic:consigaz-robo /user:desktop_app_password /pass:<senha-totvs>

# Login portal web Consigaz
cmdkey /generic:consigaz-robo /user:web_platform_password /pass:<senha-portal>
```

> **Importante:** o `cmdkey` armazena no cofre **do usuário corrente**. Se
> você rodou esses comandos como administrador, o robô (executado pelo
> usuário operacional) não vai enxergar. Rode como o usuário que vai operar.

### 4.2 Configurar o `.env` (apenas variáveis não-sensíveis)

Em `C:\consigaz-robo\.env` (não commitar):

```dotenv
PROFILE=prod
LOG_LEVEL=INFO

# Identificadores não-sensíveis
DESKTOP_APP_USERNAME=USER.TOTVS
WEB_PLATFORM_USERNAME=usuario@consigaz.com.br

# URLs
WEB_PLATFORM_BASE_URL=https://portal.consigaz.com.br

# Parâmetros de LLM (ajustar conforme custo / confiança)
LLM_MODEL=gpt-4o-mini
LLM_MIN_CONFIDENCE=0.75
```

> Os valores acima são **exemplos**. As chaves reais devem espelhar
> `src/config/settings.py`. Confira esse arquivo antes da implantação para
> não esquecer campos novos introduzidos em milestones recentes.

### 4.3 Validar credenciais carregadas

```powershell
uv run python -m orchestrator --list
```

Se a Settings falhar por segredo ausente, o exit code será **2** (config
error) e a mensagem aponta a chave faltante. Corrija e rode de novo.

### 4.4 Política de rotação

- Trocar a senha TOTVS → atualizar `cmdkey` com a nova senha; nada mais
  precisa mudar.
- Trocar a chave OpenAI → idem.
- A rotação NÃO exige redeploy nem reinício de serviço.

---

## 5. Mapeamento do TOTVS (Fase 2 — captura assistida)

Esta é a fase que **não pode ser feita remotamente "no escuro"** — exige
sessão presencial (ou call com tela compartilhada e operador real
disponível). Tempo estimado: **1 a 2 dias por fluxo de negócio** (ex.: um
fluxo = "lançar pedido de venda"; outro fluxo = "consultar saldo de
cliente").

### 5.1 Princípio operante: âncora visual, nunca coordenada

O PRD proíbe coordenadas hardcoded. Toda interação do robô com o TOTVS é:

1. **Localizar** um elemento na tela via `cv2.matchTemplate` contra um PNG
   salvo em `assets/templates/totvs/<tela>/<elemento>.png`.
2. **Calcular** a posição da ação relativa à âncora (ex.: "campo CNPJ fica
   180px à direita do label `lbl_cnpj.png`").
3. **Agir** (clique, digitação, Tab, Enter) na posição calculada.

Isso permite que pequenas mudanças de layout no TOTVS (algo ser empurrado
horizontalmente) sejam absorvidas só atualizando o PNG da âncora, sem mexer
no código Python.

### 5.2 Ciclo de captura por tela

Para cada tela do fluxo TOTVS que o robô vai operar:

#### 5.2.1 Preparar a tela

- Abrir o TOTVS no usuário do operador.
- Navegar até a tela alvo no estado "limpo" (campos vazios, modais fechados,
  rolagem no topo).
- Garantir resolução e DPI **idênticos ao uso em produção** — anotar:

  ```
  Tela: Pedido de venda - inclusão
  Resolução: 1920 x 1080
  Escala Windows: 100%
  Tema TOTVS: Padrão (claro)
  Versão TOTVS: 12.1.2310
  ```

  Anexar ao `docs/mapeamento-totvs.md` (ver §6.4).

#### 5.2.2 Capturar a tela inteira (referência)

Atalho nativo do Windows: `Win + Shift + S`, selecionar área, salvar em:

```
docs/mapeamento-totvs/<fluxo>/<NN>_<nome-da-tela>.png
```

Esse PNG **NÃO** é usado pelo robô — é só referência humana para você lembrar
do contexto durante o desenvolvimento.

#### 5.2.3 Recortar âncoras

Para cada elemento que o robô precisa localizar (label, ícone, botão), abrir
o screenshot completo no editor (Paint, Snipping Tool, GIMP) e recortar:

- **Apenas a parte estável** (texto do label + 4–6px de margem). Cortar fora
  partes que mudam (números, datas, valores).
- Salvar em PNG sem compressão lossy.
- Dimensão típica: 60×20 a 200×40 pixels.

Salvar em:

```
assets/templates/totvs/<fluxo>/<elemento>.png
```

Exemplos para um fluxo "pedido de venda":

```
assets/templates/totvs/pedido-venda/
├── lbl_codigo_cliente.png     # texto "Código:" do campo cliente
├── lbl_qtd_produto.png        # texto "Qtd:" do campo quantidade
├── btn_incluir_item.png       # ícone + texto do botão "Incluir Item"
├── btn_salvar.png             # ícone disquete + texto "Salvar"
├── icon_status_ok.png         # tick verde após salvar (âncora de sucesso)
└── msg_erro_cliente.png       # cabeçalho do modal "Cliente inválido"
```

#### 5.2.4 Anotar a ação relativa

Para cada âncora, anotar em `docs/mapeamento-totvs/<fluxo>.md`:

```markdown
### Tela: Pedido de venda - inclusão

| Passo | Âncora                | Ação                          | Observação                |
| ----- | --------------------- | ----------------------------- | ------------------------- |
| 1     | lbl_codigo_cliente    | clique (offset +180, +0)      | foca o campo Código       |
| 2     | (sem âncora)          | digitar `{{cnpj_cliente}}`    | dado vem da entrada       |
| 3     | (sem âncora)          | Tab                           | TOTVS resolve nome do PJ  |
| 4     | lbl_qtd_produto       | clique (offset +110, +0)      | foca o campo Qtd          |
| 5     | (sem âncora)          | digitar `{{quantidade}}`      |                           |
| 6     | btn_incluir_item      | clique (offset 0, 0)          | botão tem âncora completa |
| 7     | icon_status_ok        | wait_for_template (timeout 8s)| confirma item incluído    |
```

> **Heurística para offsets:** comece com (0, 0) sempre que possível
> recortando a âncora **na exata zona clicável**. Use offset apenas quando
> a âncora estável (ex.: o label) está separada do alvo (ex.: o input).
> Medir o offset com qualquer régua de pixel (PowerToys → Screen Ruler).

#### 5.2.5 Validar uma âncora isoladamente

Antes de codificar a rotina inteira, valide se cada PNG realmente é
encontrado. Crie um script descartável `scripts/probe_template.py`:

```python
"""Probe: tenta achar um template na tela atual e reporta confiança."""
import sys
from desktop.vision import wait_for_template

if __name__ == "__main__":
    path = sys.argv[1]
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    result = wait_for_template(path, timeout=timeout)
    print(f"found at {result}")
```

Rodar:

```powershell
uv run python scripts/probe_template.py assets/templates/totvs/pedido-venda/btn_salvar.png 5
```

Se reportar coordenadas → âncora boa.
Se der `TemplateNotFoundError` → recortar de novo, com margem maior ou menor;
ver §12.

### 5.3 Sessão de captura assistida (modo recomendado)

Para acelerar a §5.2, prepare um pequeno utilitário que grava a tela
inteira em PNG cada vez que o operador pressionar uma tecla:

```python
# scripts/capture_session.py (criar conforme necessário)
"""Captura screenshots da tela inteira a cada ENTER do operador.

Uso:
    uv run python scripts/capture_session.py docs/mapeamento-totvs/pedido-venda
"""
import sys
from datetime import datetime
from pathlib import Path
import pyautogui

if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    print("Pressione ENTER para capturar; Ctrl+C para sair.")
    while True:
        input()
        n += 1
        stamp = datetime.now().strftime("%H%M%S")
        path = out / f"{n:03d}_{stamp}.png"
        pyautogui.screenshot(str(path))
        print(f"  → {path}")
```

Fluxo:

1. Você inicia o script.
2. O operador executa o fluxo no TOTVS naturalmente.
3. A cada passo significativo, ele aperta ENTER no terminal e prossegue.
4. No fim você tem uma sequência ordenada de screenshots da execução real,
   pronta para recortar âncoras.

### 5.4 Mapeamento do portal web Consigaz (paralelo)

A camada web **não** usa template matching — usa seletores DOM do Playwright,
declarados em `config/selectors.json`. Em paralelo à captura do TOTVS:

1. Abrir o portal Consigaz no Chromium normal.
2. Para cada campo do formulário, abrir DevTools (`F12` → Inspector) e copiar
   o seletor mais robusto:
   - Preferir `input[name="..."]` ou `getByRole('button', { name: '...' })`.
   - Evitar seletores baseados em classes geradas (`.css-1xy23a`).
   - Evitar XPath quando houver alternativa.
3. Adicionar uma seção nova em `config/selectors.json`:

   ```jsonc
   {
     "login": { ... },           // já existe
     "pilot_smoke": { ... },     // já existe
     "totvs_pedido_venda": {     // ← nova
       "_session_sentinel": "h1:has-text('Pedido de Venda')",
       "cnpj_cliente":      "input[name='cnpjCliente']",
       "quantidade":        "input[name='qtd']",
       "observacao":        "textarea[name='obs']",
       "submit":            "button:has-text('Confirmar')"
     }
   }
   ```

> A chave `_session_sentinel` é usada por `web.session` para verificar que a
> sessão persistida ainda está válida. Escolha um seletor que **só existe
> quando logado**.

---

## 6. Estrutura de templates e seletores para TOTVS

Resumo da convenção que deve ser seguida em todos os clientes.

### 6.1 Layout em disco

```
consigaz-robo/
├── assets/
│   └── templates/
│       ├── pilot-smoke/                 # já existe (referência)
│       └── totvs/
│           ├── login/                   # tela de login do TOTVS
│           │   ├── lbl_usuario.png
│           │   ├── lbl_senha.png
│           │   └── btn_entrar.png
│           ├── menu-principal/
│           │   └── btn_modulo_vendas.png
│           └── pedido-venda/            # um fluxo = uma pasta
│               ├── lbl_codigo_cliente.png
│               ├── btn_incluir_item.png
│               ├── btn_salvar.png
│               └── icon_status_ok.png
├── config/
│   └── selectors.json                   # web-only; o desktop usa templates
└── docs/
    └── mapeamento-totvs/
        ├── pedido-venda.md              # ações relativas por âncora
        ├── pedido-venda/                # screenshots de referência
        │   ├── 001_tela_inicial.png
        │   └── 002_apos_incluir.png
        └── consulta-cliente.md
```

### 6.2 Convenção de nomes

- Tudo em minúsculas, separado por `_`.
- Prefixos sinalizam o tipo:
  - `lbl_` — label/texto fixo (âncora típica para localizar um input ao lado).
  - `btn_` — botão clicável.
  - `icon_` — ícone (sucesso, erro, status).
  - `msg_` — cabeçalho ou parte fixa de uma modal/dialog.
- O nome do elemento descreve o **propósito**, não a cor ou o pixel
  ("btn_salvar", não "btn_disquete_azul").

### 6.3 Versionamento dos templates

- Templates **são** versionados no git, exceto os de clientes específicos.
- Clientes diferentes podem ter TOTVS visualmente diferente. A solução
  recomendada:

  ```
  assets/templates/totvs/<fluxo>/        # versão "padrão" do projeto
  assets/templates/totvs.local/<fluxo>/  # override por cliente (gitignore)
  ```

  Onde `totvs.local/` está no `.gitignore` e prevalece sobre o padrão
  quando presente.

  > **Implementação:** `desktop.vision.wait_for_template(path)` recebe um
  > caminho lógico (ex.: `totvs/pedido-venda/btn_salvar.png`); a função
  > deve tentar `assets/templates/totvs.local/...` primeiro, depois cair
  > para `assets/templates/totvs/...`. Se hoje ela não faz isso, abrir
  > issue para M6 — é um pré-requisito para multi-cliente.

### 6.4 Mapeamento textual obrigatório

Para cada fluxo, manter `docs/mapeamento-totvs/<fluxo>.md` com:

- Versão do TOTVS testada.
- Resolução de tela e escala.
- Tabela de passos (âncora, ação, offset, observação) — formato do §5.2.4.
- Dados de exemplo usados na validação.
- Critérios de sucesso (que mensagem/ícone confirma "deu certo").
- Mapeamento de erros conhecidos (quais modais o TOTVS pode mostrar e como
  o robô deve reagir).

Este arquivo é **a fonte da verdade** para regenerar o mapeamento se algum
template precisar ser recapturado.

---

## 7. Criação da rotina TOTVS

A rotina é um módulo Python em `src/routines/`. Use `pilot_smoke.py` como
template (ver `src/routines/pilot_smoke.py`).

### 7.1 Esqueleto recomendado

`src/routines/totvs_pedido_venda.py`:

```python
"""Rotina TOTVS: lança um pedido de venda no ERP a partir da entrada
estruturada e replica no portal web Consigaz."""

from __future__ import annotations

from typing import Any

from desktop import (
    InteractionError,
    PlatformError,
    TemplateNotFoundError,
    click_at_template,
    extract_via_clipboard,
    get_platform_adapter,
    wait_for_template,
)
from intelligence import (
    Action,
    Decision,
    LLMResult,
    ValidationResult,
    call_llm,
    decide,
    validate,
)
from intelligence.schemas.totvs_pedido_venda import (
    TotvsPedidoVendaData,
    TotvsPedidoVendaLLM,
)
from orchestrator.context import RoutineContext
from orchestrator.registry import register
from orchestrator.types import RoutineResult
from web import close_browser, fill_form, load_selectors, navigate_to, open_browser

_TPL = "assets/templates/totvs/pedido-venda"
_PORTAL_URL = "https://portal.consigaz.com.br/pedidos/novo"


@register("totvs-pedido-venda")
def run(ctx: RoutineContext) -> RoutineResult:
    """Pipeline:
      1) trazer TOTVS ao foco
      2) extrair dados do pedido (desktop)
      3) validar com Pydantic (intelligence)
      4) call_llm para classificar observações livres
      5) decide → PROCEED_TO_WEB | ABORT | ESCALATE
      6) (se PROCEED e não dry-run) injetar no portal Consigaz
    """
    adapter = get_platform_adapter()
    adapter.focus_window("TOTVS")  # nome da janela do app

    raw = _extract_pedido_from_totvs(ctx)

    validation = validate(raw, TotvsPedidoVendaData)
    if not validation.is_valid:
        decision = decide(validation, None)
        return RoutineResult(action=decision.action, evidence=...)

    llm = call_llm(
        prompt_name="totvs-pedido-venda",
        params=raw,
        response_model=TotvsPedidoVendaLLM,
        settings=ctx.settings,
    )
    decision = decide(validation, llm, min_confidence=ctx.settings.llm_min_confidence)

    if decision.action is not Action.PROCEED_TO_WEB:
        return RoutineResult(action=decision.action, evidence=...)

    if ctx.dry_run:
        ctx.logger.info("totvs_pedido_venda_dry_run_skip_web")
        return RoutineResult(action=Action.PROCEED_TO_WEB, evidence=...)

    web_info = _submit_to_portal(ctx, validation, llm)
    return RoutineResult(action=Action.PROCEED_TO_WEB, evidence=...)


def _extract_pedido_from_totvs(ctx: RoutineContext) -> dict[str, Any]:
    """Navega no TOTVS via âncoras visuais e retorna o pedido em dict."""
    wait_for_template(f"{_TPL}/lbl_codigo_cliente.png", timeout=15)
    click_at_template(f"{_TPL}/lbl_codigo_cliente.png", offset=(180, 0))
    cnpj = extract_via_clipboard()  # Ctrl+A, Ctrl+C, pyperclip
    ...


def _submit_to_portal(ctx, validation, llm) -> dict[str, Any]:
    """Abre Playwright, navega ao portal, preenche e submete."""
    selectors = load_selectors()["totvs_pedido_venda"]
    page, browser = open_browser(ctx.settings)
    try:
        navigate_to(page, _PORTAL_URL)
        fill_form(page, selectors, data={
            "cnpj_cliente": validation.data.cnpj,
            "quantidade":   validation.data.qtd,
            "observacao":   llm.data.observacao_normalizada,
        })
        page.click(selectors["submit"])
        page.wait_for_url("**/pedidos/sucesso")
        return {"portal_status": "ok"}
    finally:
        close_browser(browser)
```

> O esqueleto acima é guia. Detalhes exatos de assinatura de
> `wait_for_template`, `click_at_template`, `open_browser` etc. devem ser
> conferidos em `src/desktop/` e `src/web/` antes de codar.

### 7.2 Schema da rotina

Criar `src/intelligence/schemas/totvs_pedido_venda.py` espelhando o padrão de
`pilot_smoke`:

- `TotvsPedidoVendaData` (Pydantic) — campos validados deterministicamente
  (CNPJ formato, quantidade > 0, etc.).
- `TotvsPedidoVendaLLM` — saída esperada da LLM (ex.: observação normalizada,
  categoria, nível de risco) com `confidence: float`.

### 7.3 Prompt da rotina

Em `config/prompts/totvs-pedido-venda.md`:

- Bloco de instrução clara, exemplos few-shot, formato JSON esperado.
- Sempre incluir disclaimer: "Se a observação contiver dados ambíguos,
  retorne `confidence < 0.5` para que `decide` rotule como ESCALATE".

### 7.4 Registro da rotina

O decorator `@register("totvs-pedido-venda")` mais a descoberta automática em
`orchestrator.registry.discover("routines")` faz com que a rotina apareça em
`--list` sem mudança adicional.

Validar:

```powershell
uv run python -m orchestrator --list
```

Deve listar `totvs-pedido-venda` ao lado de `pilot-smoke`.

---

## 8. Validação no cliente (Fase 3 — testar)

Tempo estimado: **meio dia**, no fim da Fase 2. **Sempre na máquina do
cliente**, com o TOTVS real, com dados de teste do ambiente do cliente.

### 8.1 Dry-run

Primeira execução, com `--dry-run` — exercita desktop + validação + LLM,
mas **não submete no portal web**:

```powershell
cd C:\consigaz-robo
uv run python -m orchestrator --routine totvs-pedido-venda --dry-run
```

Critério de sucesso:

- Exit code **0**.
- Log em `logs/<timestamp>_totvs-pedido-venda.json` contém o evento
  `execution_summary` com `dry_run: true`.
- Nenhuma alteração no portal web Consigaz.

Se falhar com `TemplateNotFoundError`:

- Conferir resolução / DPI iguais aos da captura.
- Reabrir o screenshot de erro em `logs/errors/` e recapturar a âncora.

Se falhar com `InteractionError`:

- Verificar se o foco do TOTVS é estável (alguma modal sobrepondo?).
- Aumentar timeout localmente para depurar; **NÃO** comitar timeout > 15s
  (regra invariante).

### 8.2 Execução real, dados controlados

Acordar com o cliente um cliente/pedido de teste descartável. Rodar **sem**
`--dry-run`:

```powershell
uv run python -m orchestrator --routine totvs-pedido-venda
```

Critério de sucesso:

- Exit code **0**.
- Pedido aparece no portal web Consigaz.
- Pedido pode ser cancelado/estornado manualmente após o teste.

### 8.3 Caminhos de falha (smoke test obrigatório)

Antes de declarar "implantado":

| Cenário                              | Como provocar                              | Comportamento esperado                                                                  |
| ------------------------------------ | ------------------------------------------ | --------------------------------------------------------------------------------------- |
| Dados inválidos no TOTVS             | CNPJ malformado / qtd negativa             | Exit code != 0; log `ABORT_IN_DESKTOP`; nada no portal web                               |
| LLM baixa confiança                  | Observação ambígua proposital              | Log `ESCALATE`; alerta para revisão humana; nada no portal web                          |
| Tela TOTVS imprevista                | Modal de erro do TOTVS antes da extração   | Exit code != 0; screenshot em `logs/errors/`; mensagem clara no log                     |
| Sessão portal web expirada           | Apagar `.web-session` antes de rodar       | Robô refaz login; sucesso na 2ª tentativa                                               |
| LLM offline                          | Desligar internet                          | Retry com backoff (tenacity); fim → exit code != 0 com mensagem `LLMUnavailableError`   |
| Crash com tela bloqueada             | Bloquear Windows manualmente antes de rodar| Falha clara; screenshot vazio aceitável; documentar para evitar em produção             |

Cada um desses cenários deve ser rodado uma vez na validação e o resultado
anotado no `docs/mapeamento-totvs/<fluxo>.md`.

### 8.4 Performance baseline

Anotar tempo de uma execução end-to-end bem-sucedida no cliente:

```
Pedido típico: ~38 s
  - desktop extract: 12 s
  - LLM: 3 s
  - web submit: 18 s
  - overhead: 5 s
```

Se ultrapassar 2 min, investigar: provavelmente template matching está
relendo muitos frames; reduzir região de busca (`region=(x,y,w,h)`).

---

## 9. Agendamento e disparo

Ver `docs/scheduling.md` para receita detalhada do Task Scheduler. Resumo
para o caso TOTVS:

### 9.1 Modos de disparo

| Modo            | Quando usar                                                  | Esforço |
| --------------- | ------------------------------------------------------------ | ------- |
| Manual (atalho) | Operador clica quando quer rodar                             | Baixo   |
| Agendado        | Lote programado (ex.: madrugada, fim de turno)               | Médio   |
| Por gatilho     | Arquivo cai numa pasta watch (planilha de entrada)           | Alto    |

**Recomendação para piloto:** começar **manual** (atalho na área de trabalho)
até o cliente confiar; subir para **agendado** depois de 2 semanas estável.

### 9.2 Atalho manual

Criar `C:\Users\Public\Desktop\Consigaz Robo - Pedido Venda.lnk`:

- Target: `powershell.exe -ExecutionPolicy Bypass -NoExit -Command "cd C:\consigaz-robo; uv run python -m orchestrator --routine totvs-pedido-venda"`
- Start in: `C:\consigaz-robo`

O `-NoExit` mantém a janela aberta no fim para o operador ver o resumo.

### 9.3 Agendado com Task Scheduler

Pré-requisitos:

- Usuário `consigaz-rpa` logado e com tela desbloqueada na hora agendada.
- Considerar auto-logon dedicado se a máquina é exclusiva do robô.

Criar tarefa:

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-ExecutionPolicy Bypass -Command `"cd C:\consigaz-robo; uv run python -m orchestrator --routine totvs-pedido-venda`"" `
  -WorkingDirectory "C:\consigaz-robo"

$trigger = New-ScheduledTaskTrigger -Daily -At 02:00

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\consigaz-rpa" `
  -LogonType Interactive -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -StartWhenAvailable -RestartCount 1 -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName "Consigaz Robo - TOTVS Pedido Venda" `
  -Action $action -Trigger $trigger -Principal $principal -Settings $settings
```

> **LogonType Interactive** é crítico — Session 0 (`ServiceAccount` /
> `Highest`) **não** funciona com PyAutoGUI.

### 9.4 Exit codes

Conforme `src/orchestrator/cli.py`:

| Code | Significado              | Ação operacional                                |
| ---- | ------------------------ | ----------------------------------------------- |
| 0    | Sucesso                  | Nenhuma                                         |
| 1    | Erro genérico            | Abrir `logs/<latest>.json`                      |
| 2    | Erro de configuração     | Verificar segredos no Credential Manager        |
| 3    | Plataforma não suportada | Errou de máquina (rodou em macOS/Linux?)        |
| 4    | Rotina desconhecida      | Checar `--list`                                 |
| 130  | Interrompido (Ctrl+C)    | Reexecutar                                      |

A receita em `docs/scheduling.md` mostra como o Task Scheduler reage a cada
um.

---

## 10. Operação, logs e suporte

### 10.1 Onde olhar quando algo falha

1. **`logs/<timestamp>_<rotina>.json`** — log estruturado, com sanitização de
   segredos. Use `jq` ou um leitor JSONL para filtrar:

   ```powershell
   Get-Content logs\20260601T140000Z_totvs-pedido-venda.json |
     ConvertFrom-Json | Where-Object level -eq 'error'
   ```

2. **`logs/<timestamp>_<rotina>.log`** — versão humana do mesmo evento.
3. **`logs/errors/<timestamp>_<rotina>.png`** — screenshot capturado no
   momento da exceção pelo `screenshot_hook`. Inestimável para depurar
   problemas de template.

### 10.2 Coleta para suporte

Quando o cliente abrir chamado, peça:

- Janela de tempo (último horário em que rodou ok / horário do erro).
- O `.json` correspondente em `logs/`.
- A pasta `logs/errors/` zipada.
- Resultado de:
  ```powershell
  uv run python -m orchestrator --list
  uv --version
  python --version
  ```

### 10.3 Política de retenção

- Manter `logs/` com rotação semanal (Task Scheduler auxiliar):

  ```powershell
  Get-ChildItem C:\consigaz-robo\logs -File |
    Where-Object LastWriteTime -lt (Get-Date).AddDays(-30) |
    Remove-Item
  ```

- `logs/errors/` guarda 90 dias (debugging vale o disco).

### 10.4 Limites de segurança operacional

- Não compartilhar `logs/errors/<...>.png` em canal público — pode conter
  dados sensíveis na tela do TOTVS.
- Compartilhar **apenas o JSON estruturado** quando possível (segredos já
  vêm mascarados como `***`).

---

## 11. Atualizações e versionamento

### 11.1 Estratégia

- **Código (rotinas, lógica, deps):** atualizado pelo desenvolvedor via
  `git pull` ou novo zip.
- **Templates de imagem do cliente** (`assets/templates/totvs.local/`):
  **nunca** sobrescritos no update — são propriedade da máquina específica.
- **Selectors web** (`config/selectors.json`): sobrescritos no update porque
  o portal web é compartilhado entre clientes.

### 11.2 Procedimento de update

```powershell
cd C:\consigaz-robo
git fetch --tags
git checkout vX.Y.Z         # versão release
uv sync                     # reinstala deps se mudou pyproject
uv run python -m orchestrator --list   # smoke
```

Em caso de regressão, rollback:

```powershell
git checkout vX.Y.(Z-1)
uv sync
```

### 11.3 Migração de dados / config

Quando uma versão exige mudança em `.env` ou novo segredo no Credential
Manager, o `CHANGELOG.md` (a ser criado) declara explicitamente. O técnico
de update executa as mudanças **antes** de rodar a nova versão.

---

## 12. Troubleshooting de campo

### 12.1 `TemplateNotFoundError` em produção (depois de funcionar)

Causa típica: alguém mudou a resolução, o tema do TOTVS, ou o TOTVS recebeu
update visual.

Ações:

1. Tirar screenshot atual da tela (`Win + Shift + S`).
2. Comparar com `docs/mapeamento-totvs/<fluxo>/<NN>_<tela>.png`.
3. Se mudou: recortar nova âncora, salvar **com o mesmo nome de arquivo**;
   commitar em `assets/templates/totvs.local/<fluxo>/` (gitignore — fica só
   no cliente) e abrir issue para atualizar o padrão upstream se aplicável.

### 12.2 PyAutoGUI não move o mouse

- Tela bloqueada → desbloquear e rodar de novo.
- Sessão remota fechada com a sessão em background → manter a sessão RDP
  aberta ou usar `tscon` para devolver a sessão ao console:
  ```powershell
  query session
  tscon <id> /dest:console
  ```

### 12.3 Playwright falha com erro de certificado

Em rede com proxy MITM:

1. Exportar o certificado da CA corporativa (`.cer`).
2. Adicionar à variável `NODE_EXTRA_CA_CERTS` antes de rodar:
   ```powershell
   $env:NODE_EXTRA_CA_CERTS = "C:\certs\corp-ca.cer"
   ```
3. Ou desabilitar o proxy MITM para o domínio do portal Consigaz.

### 12.4 LLM retornando timeout

- Conferir saída HTTPS para `api.openai.com` (alguns firewalls bloqueiam
  por idle 30 s).
- Aumentar timeout em `Settings.llm_request_timeout` se necessário (com
  consciência de custo).

### 12.5 Logs com mojibake

```powershell
chcp 65001
```

E ativar UTF-8 sistêmico (§3.6).

### 12.6 `cmdkey` salvou mas o robô não enxerga

Foi salvo no cofre do usuário errado. Logar como o usuário operacional, rodar
`cmdkey /list:consigaz-robo` — se a chave não aparecer, regravar.

---

## 13. Checklist final de aceite

Antes de declarar "implantado e pronto para produção", confirmar com o cliente
**todos** os itens abaixo:

### Ambiente

- [ ] Python 3.11+ instalado e no PATH do usuário operacional.
- [ ] `uv` instalado.
- [ ] Projeto em `C:\consigaz-robo\` (ou caminho documentado).
- [ ] `uv sync` finalizou sem erro.
- [ ] `uv run playwright install chromium` finalizou sem erro.
- [ ] `chcp 65001` aplicado ou configurado no perfil do PowerShell.

### Segurança / credenciais

- [ ] Credenciais TOTVS no Credential Manager (validado com `cmdkey /list`).
- [ ] Credenciais portal Consigaz no Credential Manager.
- [ ] Chave LLM no Credential Manager.
- [ ] `.env` em `C:\consigaz-robo\` contém apenas valores não-sensíveis.
- [ ] `PROFILE=prod` no `.env`.
- [ ] `uv run python -m orchestrator --list` lista as rotinas sem erro de
      config.

### Mapeamento

- [ ] Templates do TOTVS capturados na resolução e DPI de produção.
- [ ] `docs/mapeamento-totvs/<fluxo>.md` preenchido com versão TOTVS,
      resolução, tabela de passos.
- [ ] Cada âncora foi validada com `scripts/probe_template.py`.
- [ ] `config/selectors.json` contém a seção do portal web Consigaz para o
      fluxo.

### Rotina

- [ ] Rotina aparece em `--list`.
- [ ] Schema em `src/intelligence/schemas/<rotina>.py` revisado.
- [ ] Prompt em `config/prompts/<rotina>.md` revisado.

### Validação

- [ ] `--dry-run` passou (exit 0, sem submissão web).
- [ ] Execução real com dado de teste passou (exit 0, pedido aparece no
      portal).
- [ ] Caminhos de falha do §8.3 testados e comportamento esperado confirmado.
- [ ] Baseline de tempo registrado.

### Operação

- [ ] Modo de disparo combinado (manual / agendado / gatilho).
- [ ] Atalho de área de trabalho criado (se manual).
- [ ] Task Scheduler configurado (se agendado), com `LogonType Interactive`.
- [ ] Política de bloqueio de tela compatível com a janela de execução.
- [ ] Rotação de log configurada.
- [ ] Cliente sabe onde estão os logs e como mandar para suporte.

### Documentação

- [ ] Este guia (`docs/implantacao-cliente-totvs.md`) revisado pelo técnico.
- [ ] `docs/mapeamento-totvs/<fluxo>.md` versionado no repositório (sem
      dados sensíveis).
- [ ] Lista de contatos de suporte entregue ao cliente.

---

## 14. Anexos

### 14.1 Comandos de referência rápida

```powershell
# Setup
uv sync
uv run playwright install chromium
chcp 65001

# Operação
uv run python -m orchestrator --list
uv run python -m orchestrator --routine totvs-pedido-venda
uv run python -m orchestrator --routine totvs-pedido-venda --dry-run

# Segredos
cmdkey /list:consigaz-robo
cmdkey /generic:consigaz-robo /user:<chave> /pass:<valor>
cmdkey /delete:consigaz-robo

# Logs
Get-ChildItem logs\ | Sort-Object LastWriteTime -Descending | Select-Object -First 5
Get-Content logs\<arquivo>.json | ConvertFrom-Json | Where-Object level -eq 'error'

# Update
git fetch --tags
git checkout vX.Y.Z
uv sync
```

### 14.2 Glossário rápido

- **Âncora visual** — PNG recortado de um elemento estável da tela; o robô
  procura esse PNG na tela atual via template matching.
- **Template matching** — `cv2.matchTemplate`, retorna a posição de melhor
  correspondência da âncora na captura de tela atual.
- **Sentinela de sessão** — seletor DOM ou template visual que só existe
  quando o usuário está logado; usado para detectar sessão expirada.
- **Profile prod** — modo em que o boot do robô falha se faltar segredo
  obrigatório (não há fallback silencioso).
- **Dry-run** — execução completa do pipeline desktop + LLM, sem submissão
  no portal web. Usado para validar mapeamento sem efeitos colaterais.

### 14.3 Pontos de contato no código

| O que                      | Onde                                           |
| -------------------------- | ---------------------------------------------- |
| Adicionar rotina           | `src/routines/<nome>.py` + `@register`         |
| Schema da rotina           | `src/intelligence/schemas/<nome>.py`           |
| Prompt da rotina           | `config/prompts/<nome>.md`                     |
| Seletores web              | `config/selectors.json`                        |
| Templates desktop          | `assets/templates/totvs/<fluxo>/`              |
| Override por cliente       | `assets/templates/totvs.local/<fluxo>/`        |
| Exit codes da CLI          | `src/orchestrator/cli.py`                      |
| Settings / segredos        | `src/config/settings.py` + `keyring_source.py` |
| Hook de screenshot de erro | `src/logger/` (processors)                     |

### 14.4 Próximos fluxos TOTVS a mapear (a planejar)

O presente guia trata `pedido-venda` como exemplo. Repetir Fase 2 + Fase 3
para cada fluxo adicional contratado:

- [ ] Consulta de saldo de cliente
- [ ] Lançamento de nota fiscal
- [ ] Conferência de boleto
- [ ] (Adicionar conforme escopo do cliente)

Cada fluxo herda toda a infra de Fase 1 e Fase 4 — só requer captura de
templates + criação da rotina + selectors do portal correspondente.
