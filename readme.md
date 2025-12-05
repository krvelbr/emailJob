# Email Processing Job (`emailJob`)

## Visão Geral

Este projeto consiste em um job automatizado para processar e arquivar e-mails de um servidor de e-mail (via IMAP/POP3). O sistema foi projetado para se conectar a uma caixa de entrada, buscar novas mensagens, analisar seu conteúdo (corpo, remetente, anexos) e armazenar essas informações de forma estruturada em um banco de dados relacional.

O objetivo principal é criar um arquivo pesquisável e duradouro de comunicações por e-mail, permitindo consultas complexas, gerenciamento de dados e extração de métricas sobre as mensagens recebidas.

## Funcionalidades Principais

- **Busca de E-mails**: Conecta-se a um servidor de e-mail e busca mensagens não lidas ou novas.
- **Armazenamento no Banco de Dados**: Salva informações detalhadas de cada e-mail, incluindo:
  - Metadados (ID da Mensagem, Remetente, Destinatário, CC, Assunto, Data de Recebimento).
  - Corpo do e-mail.
- **Gerenciamento de Anexos**: Extrai anexos dos e-mails, armazena-os (geralmente em um sistema de arquivos ou storage) e associa-os ao e-mail correspondente no banco de dados.
- **Filtragem Avançada**: Permite a busca e paginação de e-mails com base em critérios como remetente, assunto ou se possui anexos.
- **Soft & Hard Delete**: Suporta a exclusão lógica (`soft delete`), que apenas marca um e-mail como excluído, e a exclusão física (`hard delete`), que o remove permanentemente do banco de dados.
- **Filtros de E-mail Configuráveis**: Permite criar regras (filtros) que podem ser aplicadas aos e-mails recebidos para executar ações futuras.
- **Monitoramento de Execução**: Cada execução do job é registrada na tabela `job_runs`, guardando métricas como o número de mensagens buscadas, salvas, status (sucesso/falha) e possíveis mensagens de erro.

## Tecnologias Utilizadas

- **Linguagem**: Python 3
- **Banco de Dados ORM**: SQLAlchemy
- **Tipagem Estática**: `typing` para um código mais robusto e claro.

## Estrutura do Projeto

# Email Processing Job (`emailJob`)

## Visão Geral

Este projeto consiste em um job automatizado para processar e arquivar e-mails de um servidor de e-mail (via IMAP/POP3, com suporte a OAuth2 para Gmail). O sistema foi projetado para se conectar a uma caixa de entrada, buscar novas mensagens, analisar seu conteúdo (corpo, remetente, anexos) e armazenar essas informações de forma estruturada em um banco de dados relacional.

O objetivo principal é criar um arquivo pesquisável e duradouro de comunicações por e-mail, permitindo consultas complexas, gerenciamento de dados e extração de métricas sobre as mensagens recebidas.

## Funcionalidades Principais

- **Busca de E-mails**: Conecta-se a um servidor de e-mail (Gmail via OAuth2) e busca mensagens.
- **Armazenamento no Banco de Dados**: Salva informações detalhadas de cada e-mail.
- **Gerenciamento de Anexos**: Extrai e armazena anexos, associando-os ao e-mail correspondente.
- **Filtragem Avançada**: Permite a busca e paginação de e-mails com base em diversos critérios.
- **Soft & Hard Delete**: Suporta exclusão lógica (marcação) e física (remoção permanente).
- **Filtros de E-mail Configuráveis**: Permite criar regras para aplicar aos e-mails recebidos.
- **Monitoramento de Execução**: Registra cada execução do job, guardando métricas de sucesso, falha e volume de dados.

## Tecnologias Utilizadas

- **Linguagem**: Python 3
- **Banco de Dados ORM**: SQLAlchemy
- **Autenticação**: Google OAuth 2.0 para acesso seguro à API do Gmail.
- **Tipagem Estática**: `typing` para um código mais robusto e claro.

## Estrutura e Descrição dos Arquivos

O projeto é modularizado para garantir a separação de responsabilidades, facilitando a manutenção e a escalabilidade.

```
.
├── app/
│   ├── main.py                 # Ponto de entrada e orquestrador do job.
│   ├── gmail_oauth_service.py  # Gerencia a autenticação com a API do Gmail.
│   ├── repositories.py         # Camada de acesso aos dados do banco.
│   ├── models.py               # Definição das tabelas do banco de dados.
│   ├── database.py             # Configuração da conexão com o banco de dados.
│   └── config.py               # Gerenciamento de configurações e variáveis de ambiente.
│
├── venv/                       # Ambiente virtual do Python (ignorado pelo .gitignore).
├── .gitignore                  # Arquivos e pastas a serem ignorados pelo Git.
└── README.md                   # Este arquivo.
```

### Descrição Detalhada dos Arquivos `.py`

- **`app/main.py`**

  - **Função**: É o ponto de entrada principal da aplicação. Este script orquestra todo o fluxo do job: carrega as configurações, inicializa a sessão com o banco de dados, utiliza o `gmail_oauth_service` para obter credenciais de acesso, conecta-se ao serviço de e-mail, busca as mensagens, usa os `repositories` para persistir os dados e, ao final, registra o resultado da execução.

- **`app/gmail_oauth_service.py`**

  - **Função**: Abstrai toda a complexidade do fluxo de autenticação OAuth 2.0 com o Google. É responsável por obter, armazenar e renovar os tokens de acesso necessários para se comunicar de forma segura com a API do Gmail. Ele garante que a aplicação sempre tenha uma credencial válida para operar.

- **`app/repositories.py`**

  - **Função**: Implementa a Camada de Acesso a Dados (Data Access Layer). Contém classes como `EmailRepository`, `AttachmentRepository`, etc., que fornecem uma interface clara para realizar operações no banco de dados (Criar, Ler, Atualizar, Deletar - CRUD). Essa camada isola o resto da aplicação dos detalhes de implementação das queries SQL/SQLAlchemy.

- **`app/models.py`**

  - **Função**: Define o schema do banco de dados usando o ORM do SQLAlchemy. Cada classe neste arquivo (`Email`, `Attachment`, `JobRun`) representa uma tabela no banco de dados, com seus respectivos campos e relacionamentos.

- **`app/database.py`**

  - **Função**: Centraliza a configuração e o gerenciamento da conexão com o banco de dados. Geralmente, contém o "engine" do SQLAlchemy e a lógica para criar e fornecer sessões de banco de dados para os repositórios e outros serviços.

- **`app/config.py`**
  - **Função**: Gerencia as configurações da aplicação. É responsável por carregar variáveis de ambiente (de um arquivo `.env` ou do sistema), como credenciais do banco de dados, chaves de API, e configurações do servidor de e-mail, disponibilizando-as de forma segura e organizada para o resto do projeto.

## Configuração e Instalação

1.  **Clonar o Repositório:**

    ```bash
    git clone https://github.com/seu-usuario/emailJob.git
    cd emailJob
    ```

2.  **Criar e Ativar o Ambiente Virtual:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

3.  **Instalar as Dependências:**

    ```bash
    pip install -r requirements.txt
    ```

    _(Nota: Crie um arquivo `requirements.txt` com as bibliotecas necessárias, como `sqlalchemy`, `google-api-python-client`, `google-auth-oauthlib`, etc.)_

4.  **Configurar Variáveis de Ambiente:**
    Crie um arquivo `.env` na raiz do projeto para armazenar as configurações sensíveis.
    ```
    DB_URL="postgresql://user:password@host:port/database"
    # Credenciais do Google Cloud para OAuth 2.0
    GOOGLE_CLIENT_ID="seu-client-id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET="seu-client-secret"
    ```

## Como Executar

Para iniciar o processo de busca e arquivamento de e-mails, execute o script principal da aplicação:

```bash
python app/main.py
```

O código é organizado para separar as responsabilidades, seguindo boas práticas de arquitetura de software.

```
.
├── app/
│   ├── models.py         # Define os modelos do banco de dados (tabelas) com SQLAlchemy.
│   ├── repositories.py   # Contém toda a lógica de acesso e manipulação de dados (CRUD).
│   └── main.py           # Orquestra a execução do job: busca, processa e salva os e-mails.
│
├── venv/                   # Ambiente virtual do Python (ignorado pelo .gitignore).
├── .gitignore              # Arquivos e pastas a serem ignorados pelo Git.
└── README.md               # Este arquivo.
```

O arquivo `app/repositories.py` é o coração da camada de acesso a dados, abstraindo as queries SQL e fornecendo uma interface clara para os serviços da aplicação.

## Configuração e Instalação

1.  **Clonar o Repositório:**

    ```bash
    git clone https://github.com/seu-usuario/emailJob.git
    cd emailJob
    ```

2.  **Criar e Ativar o Ambiente Virtual:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

3.  **Instalar as Dependências:**

    ```bash
    pip install -r requirements.txt
    ```

    _(Nota: Crie um arquivo `requirements.txt` com as bibliotecas necessárias, como `sqlalchemy`, `psycopg2-binary`, etc.)_

4.  **Configurar Variáveis de Ambiente:**
    Crie um arquivo `.env` na raiz do projeto para armazenar as configurações sensíveis.
    ```
    DB_URL="postgresql://user:password@host:port/database"
    EMAIL_HOST="imap.example.com"
    EMAIL_USER="user@example.com"
    EMAIL_PASS="password"
    ```

## Como Executar

Para iniciar o processo de busca e arquivamento de e-mails, execute o script principal da aplicação:

```bash
python app/main.py
```

O script irá se conectar ao servidor de e-mail, buscar novas mensagens, salvá-las no banco de dados conforme configurado e registrar o resultado da execução.
