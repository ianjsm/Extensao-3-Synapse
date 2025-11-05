# Assistente RAG de Requisitos com Integração Jira (Setup Local)

Este projeto é uma API web (FastAPI) que usa um modelo RAG (Retrieval-Augmented Generation) para analisar solicitações de clientes, gerar requisitos de software (como User Stories) e, após aprovação, criar 'Stories' em um projeto Jira.

Este guia foca na configuração e execução local usando um ambiente virtual Python (`venv`).

## 1\. Pré-requisitos do Sistema

1.  **Python:** Instale o **Python 3.11.x**. (O projeto foi validado com 3.11.9).
2.  **Git:** Para clonar o repositório.
3.  **(Opcional - Linux/macOS) `libmagic`:** A biblioteca `unstructured` (para ler arquivos `.md` da base de conhecimento) pode exigir `libmagic` no seu sistema.
      * **Linux (Ubuntu/Debian):** `sudo apt-get install -y libmagic-dev`
      * **macOS:** `brew install libmagic`

## 2\. Configuração e Execução Local

Siga estes passos na ordem correta.

### Passo 1: Obter o Projeto

Clone o repositório para sua máquina local e entre na pasta.

```bash
git clone [URL_DO_SEU_REPOSITORIO]
cd rag-requisitos
```

### Passo 2: Configurar Segredos (`.env`)

O projeto precisa de chaves de API para se conectar aos serviços do Google e do Jira.

1.  Copie o arquivo de template `.env.example` para um novo arquivo `.env`:
    ```bash
    # Windows (PowerShell/CMD)
    copy .env.example .env

    # macOS/Linux
    cp .env.example .env
    ```
2.  **Edite o arquivo `.env`** com um editor de texto e preencha suas credenciais reais.

### Passo 3: Criar e Ativar o Ambiente Virtual (`venv`)

Isso isola as dependências do seu projeto.

```bash
# 1. Criar o venv
python -m venv venv

# 2. Ativar o venv (Windows - PowerShell/CMD)
.\venv\Scripts\activate

# 2. Ativar o venv (macOS / Linux)
# source venv/bin/activate
```

Você verá `(venv)` no início do seu prompt se funcionar.

### Passo 4: Instalar as Dependências

O arquivo `requirements.txt` deste projeto contém a lista *principal* de pacotes. O Pip cuidará de resolver as sub-dependências (como `urllib3` e `kubernetes`) automaticamente, evitando conflitos.

```bash
pip install -r requirements.txt
```

### Passo 5: Executar a Ingestão de Dados (Obrigatório)

Este é um passo **crucial**. Este script lê os arquivos da pasta `/documentos`, os processa e cria o banco de dados vetorial (`/chroma_db`) que a API usará.

Execute-o uma vez antes de iniciar a API (e novamente sempre que você atualizar os `/documentos`):

```bash
python app/ingest.py
```

Aguarde até ver a mensagem "--- Ingestão Concluída com Sucesso\! ---".

### Passo 6: Executar a API Principal

Agora, inicie o servidor web FastAPI. Este comando ficará rodando.

```bash
python main.py
```

O terminal mostrará que o servidor está rodando em `http://127.0.0.1:8000`.

### Passo 7: Testar a API

Seu backend está 100% online.

1.  Abra seu navegador e acesse a documentação interativa:
    **`http://127.0.0.1:8000/docs`**
2.  Ou use o **Postman** (recomendado para este fluxo).

## 3\. Como Usar a API (Fluxo de Trabalho de Teste)

Use o Postman ou a interface `/docs` para simular o fluxo:

1.  **Execute `POST /start_analysis`:**

      * Cole o texto bruto da entrevista do cliente no campo `client_request`.
      * Clique em "Execute".
      * Copie os valores `generated_requirements` e `history` da resposta.

2.  **Execute `POST /refine` (Opcional):**

      * Cole o `history` que você copiou no campo `history`.
      * Escreva sua instrução de refinamento (ex: "No requisito 3, adicione...") no campo `instruction`.
      * Execute. O assistente responderá com os requisitos atualizados.
      * Repita este passo quantas vezes for necessário, sempre usando o `history` mais recente da última resposta.

3.  **Execute `POST /approve`:**

      * Quando estiver satisfeito, copie o `final_requirements` da última resposta (seja do `/start_analysis` ou do último `/refine`).
      * Copie o `original_request` (o texto do cliente que você usou no passo 1).
      * Cole-os nos campos correspondentes e execute.
      * O sistema criará os tickets individuais no Backlog do seu projeto Jira.
