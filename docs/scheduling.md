# Agendamento — receitas operacionais

Este documento descreve como agendar o robô (`consigaz-robo`) em produção via
cron + LaunchAgent no macOS e via Task Scheduler no Windows, como interpretar
os exit codes e como inspecionar o log estruturado.

> Pré-requisito: o robô instala um console-script `consigaz-robo` (ver
> `pyproject.toml`). Equivalente a `python -m orchestrator`.

---

## Sumário rápido

- Listar rotinas registradas: `consigaz-robo --list`
- Executar rotina: `consigaz-robo --routine <nome>`
- Dry-run (sem submit web): `consigaz-robo --routine <nome> --dry-run`
- Inspeção: `grep '"event":"execution_summary"' logs/*.json | jq .`

---

## Exit codes

Tabela de exit codes do orquestrador. **Cron/LaunchAgent/Task Scheduler usam
estes códigos para decidir alertar, reagendar ou ignorar.**

| Exit | Causa                                                       | Tratamento sugerido                                  |
|-----:|-------------------------------------------------------------|------------------------------------------------------|
|  `0` | Sucesso (`Action.PROCEED_TO_WEB` ou rotina sem exceção)     | Sem ação                                             |
|  `1` | Falha genérica não classificada (`Exception` na rotina)     | Alertar engenharia; checar `.log`/`.json`            |
|  `2` | Erro de configuração (`pydantic.ValidationError`, env var)  | Não reagendar; falha persistente até corrigir env    |
|  `3` | Plataforma não suportada (`UnsupportedPlatformError`)       | Não reagendar; corrigir host                         |
|  `4` | Rotina desconhecida (`UnknownRoutineError`/registry)        | Verificar deploy: rotina não chegou na máquina       |
|  `5` | Rotina decidiu abortar (`ABORT_IN_DESKTOP`/`RAISE_EXCEPTION`)| Rodou mas não executou — checar evidence do summary  |
| `130`| Interrompido por `KeyboardInterrupt` / SIGINT               | Esperado em parada manual                            |

---

## macOS

### Opção A — `crontab`

Mais simples. Adequado para uma máquina única, baixa frequência.

```bash
# Edição
crontab -e

# Exemplo: rodar `extracao-diaria` todo dia útil às 07:30
30 7 * * 1-5 /usr/local/bin/consigaz-robo --routine extracao-diaria \
    >> /Users/consigaz/logs/cron.stdout 2>> /Users/consigaz/logs/cron.stderr
```

Notas:
- Use caminho absoluto do binário (ou do `python -m orchestrator` dentro do venv).
- `LOG_DIR` (env do `Settings`) controla onde sai o `.log`/`.json` estruturado.
- Cron envia e-mail em falhas se `MAILTO=` estiver definido no crontab.

### Opção B — LaunchAgent (`.plist`)

Recomendado em macOS moderno: melhor controle, sobrevive a logout, logs
explícitos.

Salve em `~/Library/LaunchAgents/com.consigaz.robo.extracao-diaria.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.consigaz.robo.extracao-diaria</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/consigaz-robo</string>
        <string>--routine</string>
        <string>extracao-diaria</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/consigaz/robo</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>LOG_DIR</key>
        <string>/Users/consigaz/robo/logs</string>
        <key>PROFILE</key>
        <string>prod</string>
    </dict>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>7</integer>
        <key>Minute</key><integer>30</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/consigaz/robo/logs/launchd.stdout</string>
    <key>StandardErrorPath</key>
    <string>/Users/consigaz/robo/logs/launchd.stderr</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

Ative:

```bash
launchctl load ~/Library/LaunchAgents/com.consigaz.robo.extracao-diaria.plist
launchctl list | grep consigaz
```

---

## Windows

### Opção A — `schtasks` (linha de comando)

```cmd
schtasks /Create ^
    /TN "ConsigazRoboExtracaoDiaria" ^
    /TR "C:\Path\To\.venv\Scripts\consigaz-robo.exe --routine extracao-diaria" ^
    /SC DAILY /ST 07:30 ^
    /RL HIGHEST /F
```

- `/RL HIGHEST` roda elevado (necessário se algum app desktop exigir).
- O Task Scheduler captura o exit code; visualize em "Last Run Result".

### Opção B — XML para importar via GUI

Salve como `consigaz-extracao-diaria.xml` e importe em
`Task Scheduler → Import Task...`:

```xml
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Robô RPA Consigaz — rotina extracao-diaria</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T07:30:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
      <Enabled>true</Enabled>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>C:\Path\To\.venv\Scripts\consigaz-robo.exe</Command>
      <Arguments>--routine extracao-diaria</Arguments>
      <WorkingDirectory>C:\Path\To\robo</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

---

## Inspecionando o `execution_summary`

Cada execução emite **uma** linha de log estruturado com o evento
`execution_summary`. Os campos principais:

| Campo          | Tipo     | Significado                                                    |
|----------------|----------|----------------------------------------------------------------|
| `routine`      | string   | Nome despachado                                                |
| `action`       | string   | `proceed_to_web` / `abort_in_desktop` / `raise_exception` / `error` |
| `duration_s`   | float    | Duração total da execução em segundos (3 casas)                |
| `tokens_in`    | int      | Tokens de entrada acumulados em chamadas LLM                   |
| `tokens_out`   | int      | Tokens de saída                                                |
| `cost_usd`     | float    | Custo estimado em USD (4 casas)                                |
| `exit_code`    | int      | Exit code retornado ao SO                                      |
| `dry_run`      | bool     | Se a flag `--dry-run` estava ligada                            |
| `started_at`   | string   | ISO 8601 UTC                                                   |
| `finished_at`  | string   | ISO 8601 UTC                                                   |
| `evidence_keys`| array    | Apenas as **chaves** do evidence (sem valores — anti-PII)      |
| `error_type`   | string   | Presente quando `action == "error"` ou `"boot_error"`          |
| `error_msg`    | string   | Mensagem do erro                                               |

Filtrar com `jq`:

```bash
# Última execução de cada rotina (campos chave)
grep '"event":"execution_summary"' logs/*.json \
  | jq -c '{routine, action, exit_code, duration_s, tokens_in, tokens_out, cost_usd}'

# Soma de custo do dia
grep '"event":"execution_summary"' logs/$(date +%Y%m%d)*.json \
  | jq -s 'map(.cost_usd) | add'

# Só falhas
grep '"event":"execution_summary"' logs/*.json \
  | jq -c 'select(.exit_code != 0)'
```

Quando o boot falha antes do logger inicializar, o sumário sai como **JSON
puro em stderr** (`{"event":"execution_summary","action":"boot_error",...}`).
Capture stderr no agendador (`StandardErrorPath` no LaunchAgent, redirect em
crontab) para não perder esse registro.

---

## Convenções

- Uma rotina por LaunchAgent / Task. Não junte várias num só job.
- Não rode o robô como root/`SYSTEM` a menos que a rotina exija — interações
  com app desktop falham se a sessão gráfica for diferente.
- Aposentou uma rotina? Remova o `.plist` / task — o registry pode mudar; o
  agendador não percebe sozinho.
