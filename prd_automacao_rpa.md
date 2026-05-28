# Documento de Requisitos do Produto (PRD)
## Projeto: Robô de Automação Híbrida (RPA Desktop & Web)

---

## 1. Visão Geral do Produto
O objetivo deste projeto é desenvolver uma solução de Automação de Processos Robóticos (RPA) de arquitetura híbrida e modular, projetada especificamente para rodar de forma nativa e otimizada no ecossistema macOS (incluindo arquiteturas Apple Silicon). O robô será capaz de interagir de forma automatizada com aplicativos locais (Desktop) e sistemas em navegadores (Web), realizando navegação entre telas, preenchimento inteligente de campos, extração de relatórios e análise lógica e semântica de dados através da integração com Modelos de Linguagem Avançados (LLMs).

---

## 2. Objetivos e Metas
* **Eficiência Operacional:** Reduzir o tempo gasto em tarefas repetitivas de preenchimento e conferência de dados em pelo menos 70%.
* **Confiabilidade de Dados:** Eliminar erros humanos de digitação e transferência de informações entre o sistema local e a plataforma web.
* **Modularidade e Escabilidade:** Criar uma base de código modular em Python que permita adicionar novas rotinas de forma simples, isolando a lógica de interface Desktop da interface Web.
* **Tomada de Decisão Automatizada:** Implementar uma camada de inteligência capaz de classificar e analisar textos livres extraídos dos sistemas antes de tomar a próxima ação estruturada.

---

## 3. Arquitetura Técnica e Stack Tecnológica
A arquitetura do sistema será dividida em módulos independentes coordenados por um script central de orquestração.

* **Linguagem Base:** Python 3.11+
* **Automação Desktop:** * `PyAutoGUI` para controle de mouse e teclado.
    * `OpenCV` (através do `opencv-python`) para reconhecimento de padrões visuais e localização de elementos em tela por imagem (Computer Vision).
    * `AppleScript` (via subprocessos Python) para garantir o foco nativo e manipulação de janelas no macOS.
* **Automação Web:** * `Playwright` para automação headless/headed de navegadores, garantindo velocidade e imunidade a quebras de layout baseadas em coordenadas.
* **Camada de Inteligência e Processamento:**
    * `Pandas` para manipulação estruturada das análises e logs.
    * Integração via API com provedores de IA generativa (OpenAI/Anthropic) para processamento de linguagem natural e tomadas de decisão complexas.

---

## 4. Requisitos Funcionais (FR)

### Módulo 1: Orquestração e Inicialização (Core)
* **FR-1.1:** O sistema deve inicializar um ambiente seguro e verificar as dependências necessárias antes de iniciar qualquer rotina.
* **FR-1.2:** O robô deve possuir uma rotina de gerenciamento seguro de credenciais (variáveis de ambiente `.env` ou Keychain local) para login nos sistemas sem exposição de senhas no código.
* **FR-1.3:** O script deve gerar logs detalhados de cada etapa executada (sucesso, aviso, erro) em arquivos locais formatados em `.log` ou `.json`.

### Módulo 2: Automação Desktop (Aplicativo Local)
* **FR-2.1:** O robô deve ser capaz de abrir o aplicativo local especificado utilizando comandos nativos do macOS (`open -a`).
* **FR-2.2:** O robô deve aguardar o carregamento da interface gráfica utilizando checagem dinâmica de presença de imagem (ancoragem visual via OpenCV) em vez de pausas estáticas (`time.sleep`).
* **FR-2.3:** O sistema deve interagir com os campos do aplicativo desktop realizando cliques precisos nas coordenadas identificadas pelas imagens de âncora.
* **FR-2.4:** O robô deve limpar os campos antes de inserir novos textos e utilizar atalhos nativos do sistema (ex: `Command + A`, `Command + C`) para extrair dados da interface para a área de transferência.

### Módulo 3: Automação Web (Navegador)
* **FR-3.1:** O módulo Web deve iniciar uma instância do navegador controlada pelo Playwright, reaproveitando estados de sessão (cookies/tokens) quando aplicável para evitar logins repetitivos.
* **FR-3.2:** O robô deve navegar por URLs parametrizadas e localizar elementos de formulários estritamente através de seletores DOM robustos (Xpath, CSS selectors, text roles), evitando dependência visual.
* **FR-3.3:** O sistema deve realizar o preenchimento de formulários web multi-etapas, lidando nativamente com carregamentos assíncronos e modais/pop-ups inesperados.

### Módulo 4: Processamento e Análise Inteligente de Dados
* **FR-4.1:** O sistema deve estruturar os dados capturados do aplicativo desktop em um formato limpo (Dicionário ou DataFrame Pandas).
* **FR-4.2:** O robô deve aplicar regras lógicas de validação (ex: campos obrigatórios vazios, formatos de data incorretos, valores fora do padrão).
* **FR-4.3:** Para campos contendo textos não estruturados ou feedbacks textuais, o robô deve disparar uma requisição assíncrona para a API da LLM selecionada para extrair sentimento, intenção ou categorização baseada em um prompt pré-definido.
* **FR-4.4:** Com base no veredito da análise (estruturada ou por IA), o robô deve decidir o fluxo condicional subsequente (ex: se aprovado, envia para a web; se reprovado, marca como exceção no desktop).

---

## 5. Requisitos Não-Funcionais (NFR)
* **NFR-5.1 (Performance):** O script Python e suas respectivas bibliotecas pesadas (como OpenCV) devem rodar de forma nativa na arquitetura ARM64 (Apple Silicon), garantindo baixo consumo de memória e CPU.
* **NFR-5.2 (Confiabilidade e Resiliência):** O robô deve implementar uma política estrita de *Try-Catch* em todas as interações de tela. Caso um elemento não seja encontrado em até 15 segundos, o robô deve capturar um screenshot da tela atual, salvar na pasta de erros e encerrar a rotina de forma graciosa sem corromper os dados.
* **NFR-5.3 (Manutenibilidade):** O código deve seguir estritamente os princípios do Clean Code, com separação clara de responsabilidades: seletores visuais e seletores web devem ficar guardados em arquivos de configuração separados (`config.py` ou `selectors.json`), facilitando ajustes rápidos em caso de mudança de layout dos sistemas.
* **NFR-5.4 (Segurança):** Dados sensíveis trafegados em memória devem ser limpos após a execução do ciclo, e nenhuma informação protegida por sigilo ou LGPD deve ser gravada em logs abertos.

---

## 6. Fluxo de Execução Padrão (Happy Path)
1. O Orquestrador inicia o ambiente e carrega as configurações.
2. O AppleScript traz o aplicativo Desktop para o primeiro plano ou inicia o processo.
3. O OpenCV localiza a tela de login/home do app local.
4. O PyAutoGUI preenche as informações e navega pelas telas necessárias.
5. O robô extrai os dados alvo textuais e numéricos e os armazena temporariamente na memória.
6. A camada de dados valida as informações e processa strings de texto livre via API de inteligência artificial.
7. O Playwright abre o navegador em segundo plano (ou visível para auditoria).
8. O robô web navega até o formulário de destino e injeta os dados tratados e analisados nos campos adequados.
9. O Playwright confirma o envio, captura o ID de sucesso da transação e encerra a sessão web.
10. O Orquestrador grava o log de sucesso e encerra o ciclo de automação.

---

## 7. Riscos e Mitigações
* **Risco 1: Mudança de interface no Aplicativo Desktop.** Se o design do app local mudar, o PyAutoGUI pode perder a referência de clique.
    * *Mitigação:* Isolar todos os recortes de imagens de ancoragem em uma pasta dedicada (`/assets/templates/`) e centralizar as margens de tolerância de correspondência visual do OpenCV em um único arquivo de configuração.
* **Risco 2: Instabilidade na rede durante chamadas de API (Web ou LLM).**
    * *Mitigação:* Implementar mecanismos de *retry* com espaçamento de tempo exponencial (*exponential backoff*) para requisições HTTP e chamadas de IA.
* **Risco 3: Bloqueio de automação ou CAPTCHAs na plataforma Web.**
    * *Mitigação:* Configurar cabeçalhos de navegação humanos estáveis no Playwright, evitar comportamentos perfeitamente lineares e usar sessões persistentes para minimizar desafios de login.
