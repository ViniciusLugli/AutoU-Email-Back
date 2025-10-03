# AutoU - Backend (FastAPI)

Este repositório contém o backend FastAPI do desafio técnico. A API recebe e-mails (texto ou arquivo), aplica
pré-processamento de NLP, classifica o conteúdo e gera uma sugestão de resposta automática. O processamento pesado
é executado por um worker Celery (assíncrono); histórico e resultados são persistidos em um banco relacional via SQLModel.

Visão rápida

- Endpoints protegidos por JWT para criar/consultar textos e gerenciar usuários
- Pipeline assíncrono: upload/recebimento do texto → criação de TextEntry (PROCESSING) → Celery worker processa NLP + IA → update (COMPLETED/FAILED)
- Geração de texto feita via cliente `google.genai` (SDK) — parâmetros controláveis por variáveis de ambiente

## Tecnologias utilizadas

- Python 3.13
- FastAPI (ASGI)
- SQLModel (SQLAlchemy)
- Alembic (migrations)
- Celery (task queue)
- Redis (recomendado) — broker e opcionalmente backend de resultados do Celery
- google.genai (SDK) para geração de texto (LLM)
  -- spaCy para pré-processamento de texto
  -- pdfplumber para leitura de PDFs
- Uvicorn para executar a aplicação ASGI
- Docker (imagem fornecida via `Dockerfile` no repositório)

## Sumário do README

- Endpoints (rotas) com exemplos de request/response e códigos de status
- Como usar o Swagger UI (`/docs`) e a OpenAPI (`/openapi.json`)
- Configuração local (variáveis de ambiente, banco, Celery)
- Rodando com Docker
- Testes e desenvolvimento

## Swagger UI (/docs)

O FastAPI expõe automaticamente a documentação interativa Swagger no endpoint `/docs` quando a aplicação está rodando.
Abra `http://localhost:8000/docs` (ou a porta em que o Uvicorn estiver escutando) para ver todas as rotas, modelos de
request/response, e testar endpoints diretamente do navegador.

Também é disponibilizada a especificação OpenAPI em `/openapi.json`.

## Endpoints e formatos (rotas atuais)

Observação: muitos endpoints exigem autenticação Bearer (JWT). Os modelos Pydantic estão em `app/schemas.py` e os nomes
de resposta usados abaixo referenciam essas classes.

1. Registrar usuário

- Método: POST
- Endpoint: `/auth/register`
- Body (application/json):

```json
{ "username": "string", "email": "string@example.com", "password": "senha" }
```

- Response: 200 OK
- Response model: `UserResponse`

2. Login

- Método: POST
- Endpoint: `/auth/login`
- Body (application/json):

```json
{ "email": "string@example.com", "password": "senha" }
```

- Response: 200 OK
- Response model: `TokenResponse` — ex.:

```json
{ "access_token": "<jwt>", "token_type": "bearer", "user_id": 1 }
```

3. Processar e-mail (enfileirar)

- Método: POST
- Endpoint: `/texts/processar_email`
- Autenticação: Bearer token
- Content-Type: multipart/form-data
- Form fields (uma das duas opções obrigatória):

  - `file` (UploadFile) — um PDF/txt anexo, ou
  - `text` (string) — corpo do e-mail

- Success response (quando a tarefa é enfileirada): 200 OK

```json
{ "task_id": "<celery-task-id>", "status": "queued" }
```

- Error responses:
  - 400 Bad Request — quando `text` e `file` estão vazios
  - 401 Unauthorized — quando o token está ausente/inválido
  - 503 Service Unavailable — quando o enqueue para Celery falha

Notes:

- A rota grava temporariamente o arquivo enviado em `data/` (ou pasta configurada) e passa o caminho ao worker Celery.
- O worker atual executa `process_pipeline_async` (em `app/services/tasks.py`) que:
  1. cria um `TextEntry` com status `PROCESSING`,
  2. executa o pipeline de NLP + IA,
  3. atualiza o registro com `category`, `generated_response` e `status = COMPLETED` (ou `FAILED`).

4. Listar textos do usuário

- Método: GET
- Endpoint: `/texts/`
- Autenticação: Bearer token
- Response: 200 OK
- Response model: list[`TextEntryResponse`]

Exemplo de `TextEntryResponse`:

```json
{
  "id": 1,
  "user_id": 1,
  "status": "COMPLETED",
  "original_text": "Olá, ...",
  "category": "PRODUTIVO",
  "created_at": "2025-09-28T12:34:56.789Z",
  "generated_response": "Olá, obrigado...",
  "file_name": null
}
```

5. Deletar um texto

- Método: DELETE
- Endpoint: `/texts/{text_id}`
- Autenticação: Bearer token
- Success response: 204 No Content
- Error: 404 Not Found — quando o `text_id` não existir ou for de outro usuário

6. Listar usuários

- Método: GET
- Endpoint: `/users/`
- Autenticação: Bearer token
- Response: 200 OK
- Response model: list[`UserResponse`]

7. Informações do usuário atual

- Método: GET
- Endpoint: `/users/me`
- Autenticação: Bearer token
- Response: 200 OK
- Response model: `UserResponse`

8. Atualizar usuário atual

- Método: PUT
- Endpoint: `/users/me`
- Autenticação: Bearer token
- Query params (opcionais): `username`, `email`, `password`
- Response: 200 OK — retorna `UserResponse` atualizado

9. Deletar usuário atual

- Método: DELETE
- Endpoint: `/users/me`
- Autenticação: Bearer token
- Success response: 204 No Content

10. Health (DB)

- Método: GET
- Endpoint: `/health/db`
- Response: 200 OK
- Exemplo de resposta:

```json
{ "db": true }
```

## Modelos / Schemas principais

- `UserCreateRequest` — request para registrar
- `UserResponse` — resp. com `id`, `username`, `email`, `texts`
- `TextEntryCreateRequest` — interno para criar registros
- `TextEntryResponse` — `id`, `user_id`, `status`, `original_text`, `category`, `created_at`, `generated_response`, `file_name`
- `TokenResponse` — `access_token`, `token_type`, `user_id`
- `ProcessResultResponse` — `category`, `confidence`, `generated_response`
- `TaskStatusResponse` — `task_id`, `status`, `result` (opcional)

## Variáveis de ambiente (essenciais)

- `DATABASE_URL` — URL do banco (ex: `sqlite+aiosqlite:///./dev.db`)
- `SECRET_KEY` — chave JWT
- `ALGORITHM` — algoritmo JWT (ex: `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` — expiração do token (minutos)
- `GENAI_API_KEY` — chave para `google.genai` (quando aplicável)
- `GENAI_MODEL` — nome do modelo a usar (opcional)
  -- `GENAI_MAX_OUTPUT_TOKENS` — limite de tokens de saída (ex: `2056`)
  -- `GENAI_TEMPERATURE` — temperatura do gerador (ex: `0.0`)
- `USE_CELERY` — `true`/`false` para habilitar enfileiramento (recomendado true em produção)
- `CELERY_BROKER_URL` — ex: `redis://localhost:6379/1`
- `CELERY_RESULT_BACKEND` — ex: `redis://localhost:6379/2`
- `ALLOWED_ORIGINS` — CORS (vírgula separado)

## Executando localmente (passos)

1. Crie e ative um virtualenv e instale dependências:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Configure variáveis de ambiente (exemplo mínimo):

```bash
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
export SECRET_KEY="sua-secret-key"
export ACCESS_TOKEN_EXPIRE_MINUTES=60
export USE_CELERY=false
```

3. Inicialize banco (SQLite):

```bash
python -c "from app.db import init_db; import asyncio; asyncio.run(init_db())"
```

4. Rodar a API (desenvolvimento):

```bash
uvicorn app.main:app --reload --port 8000
```

5. Rodar Celery worker (quando `USE_CELERY=true`):

```bash
celery -A app.services.celery.celery worker --loglevel=info
```

Executando web + worker juntos (script `app/run.py`)

O projeto inclui um pequeno utilitário `app/run.py` destinado a facilitar o desenvolvimento local quando você quer subir
o servidor ASGI (Uvicorn) e um worker Celery no mesmo processo pai (cada um em um processo filho separado).

Como funciona:

- `app/run.py` cria um processo separado para executar o worker Celery via `multiprocessing.Process` e em seguida
  inicia o Uvicorn apontando para `app.main:app`.
- É útil para desenvolvimento local rápido, evitando que você tenha que abrir dois terminais distintos.

Como usar:

```bash
python -m app.run
```

Observações importantes:

- Em produção não é recomendado rodar web e worker no mesmo host/processo. Use processos separados e orquestração (systemd, docker-compose, Kubernetes, etc.).
- O script inicia o Celery com `--concurrency=1` e `--autoscale=2,1` por padrão; ajuste conforme necessário via edição do script ou passando variáveis de ambiente.
- Se o worker depende de serviços externos (Redis, banco), assegure que esses serviços estejam acessíveis antes de iniciar `app/run.py`.

## Rodando com Docker

- Há um `Dockerfile` no repositório para criar uma imagem que execute a API com Uvicorn. Em um ambiente com Docker instalado, crie a imagem e rode:

```bash
docker build -t autou-email-back .
docker run -e DATABASE_URL="sqlite+aiosqlite:///./dev.db" -p 8000:8000 autou-email-back
```

Para orquestrar web + worker + redis, crie um `docker-compose.yml` com serviços `web`, `worker` e `redis` (opcional, não incluído por padrão).

## Debug & diagnóstico de geração (GenAI)

- Aumente `GENAI_MAX_OUTPUT_TOKENS` (ex.: 2056) se o modelo estiver cortando a saída.

Observação: o projeto não persiste respostas brutas dos modelos em disco por motivos de segurança e privacidade. Para diagnóstico mais profundo, capture os logs do worker Celery em modo debug e compartilhe trechos relevantes (sem dados sensíveis).
