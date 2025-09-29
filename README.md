# AutoU - Backend (FastAPI)

## Resumo

Este repositório contém o projeto que estou desenvolvendo como parte de um **teste técnico para a AutoU**. A solução é um backend em FastAPI que recebe emails (texto ou PDF/arquivo), aplica pré-processamento de NLP, classifica o e-mail como "Produtivo" ou "Improdutivo" usando modelos de IA e gera uma sugestão de resposta. O processamento pesado é enfileirado via Celery; resultados e histórico são armazenados em um banco relacional (SQLModel / PostgreSQL / SQLite em testes).

Principais funcionalidades

- Receber texto ou upload de arquivo (PDF/txt) para processar um e-mail.
- Pré-processamento de texto (remoção de stopwords, lematização, extração de keywords).
- Classificação do texto em categorias (Produtivo / Improdutivo) via pipeline IA (Hugging Face local ou API externa).
- Geração de sugestão de resposta (modelo de geração de texto ou fallback simples).
- Persistência do histórico por usuário (TextEntry) com status (PROCESSING, COMPLETED, FAILED).
- Autenticação via JWT (register/login) e rotas protegidas.

## Tecnologias

- Python 3.13

## Sumário

- Visão geral do projeto
- Contexto do desafio (fornecido)
- Objetivos esperados
- Arquitetura e tecnologias
- Rotas (endpoints) com exemplos de request/response
- Diagrama do fluxo de processamento
- Como rodar localmente
- Notas e recomendações

## Visão geral

Este projeto é uma **API backend** que recebe emails (texto ou arquivo) e automatiza:

1. Pré-processamento de texto (NLP)
2. Classificação do email em categorias (Produtivo / Improdutivo)
3. Geração de resposta automática sugerida
4. Persistência do histórico e status do processamento

O processamento pesado é enfileirado via Celery para que o endpoint responda rapidamente com um identificador de tarefa (`task_id`) enquanto o worker executa NLP + IA e atualiza o banco de dados.

## Contexto do desafio (trecho oficial)

Estamos criando uma solução digital para uma grande empresa do setor financeiro que lida com um alto volume de emails diariamente. Esses emails podem ser solicitações de status, uploads de arquivos, ou comunicações improdutivas.

### Objetivo do desafio simplificado

Desenvolver uma aplicação web simples que utilize IA para:

- Classificar emails em categorias predefinidas (Produtivo / Improdutivo)
- Gerar sugestões de resposta automática baseadas na classificação

### Categorias

- **Produtivo**: emails que exigem ação ou resposta específica
- **Improdutivo**: emails que não exigem ação imediata

## Arquitetura & Tecnologias

- FastAPI (ASGI)
- Python 3.13
- SQLModel (por cima de SQLAlchemy)
- Celery (worker) para processamento assíncrono
- Redis (recomendado) como broker para Celery
- Hugging Face Transformers (ou API externa) para classificação e geração
- spaCy para pré-processamento (stopwords, lematização)
- pdfplumber para leitura de PDFs
- pytest + pytest-asyncio + httpx para testes

### Componentes principais

- `app/main.py` — instancia o FastAPI e monta as rotas
- `app/routes/*` — rotas: `auth`, `texts`, `users`, `health`
- `app/services/*` — implementação da pipeline (nlp, ia, tasks, leitura de arquivo)
- `app/models.py` — SQLModel: `User`, `TextEntry`
- `app/crud.py` — operações DB (sync/async)

## Rotas principais (exemplos)

### 1) Registrar usuário

- Método: POST
- Endpoint: `/auth/register`
- Body JSON:

```json
{
  "username": "string",
  "email": "string@example.com",
  "password": "senha"
}
```

- Response: `UserResponse` (sem senha)

### 2) Login

- Método: POST
- Endpoint: `/auth/login`
- Body JSON:

```json
{ "email": "string@example.com", "password": "senha" }
```

- Response: `{ "access_token": "...", "token_type": "bearer" }`

### 3) Processar e-mail

- Método: POST
- Endpoint: `/texts/processar_email`
- Autenticação: Bearer token
- Accepts (multipart/form-data):
  - `file` (UploadFile), ou
  - form field `text` (string)
- Example (form): `text=Olá, preciso atualizar o pedido #123`
- Response:

```json
{ "task_id": "task-abc", "status": "queued" }
```

> Observação: a rota enfileira uma tarefa Celery chamada `process_pipeline_task`.

### 4) Listar textos do usuário

- Método: GET
- Endpoint: `/texts/`
- Autenticação: Bearer token
- Response: lista de objetos `TextEntry`

### 5) Listar usuários (protegido)

- Método: GET
- Endpoint: `/users/`

## Detalhes técnicos sobre `process_pipeline_task`

Fluxo resumido da task:

1. Ler arquivo via `read_file_sync(file_path)` ou usar `text` enviado
2. Criar registro `TextEntry` no DB com `status = PROCESSING`
3. Rodar `nlp_service.preprocess_sync` para limpar e extrair features
4. Rodar `ia_service.infer_sync` para classificar e gerar resposta
5. Atualizar `TextEntry` com `category`, `generated_response` e `status = COMPLETED` (ou `FAILED`)
6. Deletar arquivo temporário (se aplicável)

## Diagrama do processo

```mermaid
flowchart TD
    A[Usuário] -->|Login/Cadastro| B[Frontend - React + Tailwind]
    A -->|Envia texto ou PDF| B

    B -->|Requisições HTTP| C[Backend - FastAPI]

    C --> D[Autenticação - JWT]
    D -->|Token JWT| B

    C --> E[NLP - spaCy/pdfplumber]
    E --> F[IA - Gemini (API) ou HF Transformers (local)]
    F --> G[Categoria + Resposta sugerida]

    C --> H[(PostgreSQL - Usuários e histórico)]
    C --> I[(Redis - Cache de resultados)]

    G --> C
    C --> B
    B -->|Exibe resultados| A

```

## Como rodar localmente (rápido)

1. Instale dependências (venv recomendado):

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Variáveis de ambiente mínimas:

```bash
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
export SECRET_KEY="sua-secret-key"
export ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES=60
```

3. Inicialize DB (para SQLite a função `init_db()` já cria as tabelas):

```bash
python -c "from app.db import init_db; import asyncio; asyncio.run(init_db())"
```

4. Rodar FastAPI (desenvolvimento):

```bash
uvicorn app.main:app --reload
```

5. Rodar Celery worker (opcional, para processamento assíncrono real):

```bash
celery -A app.services.celery.celery worker --loglevel=info
```

## Testes

- `pytest -q` (os testes de integração usam `pytest-asyncio` e `httpx.ASGITransport`).
- Os testes atuais cobrem autenticação, enfileiramento de tarefas e listagem de textos.
