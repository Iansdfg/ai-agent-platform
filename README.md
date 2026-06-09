# AI Agent Platform (Market Brain Agent)

A production-style AI Marketing Agent platform example. The project demonstrates how an extensible agent backend can combine an API layer, LangGraph orchestration, RAG, tool execution, database persistence, and tracing.

## Project Overview

Market Brain Agent currently supports:

- RAG-based Q&A: retrieves context from documents in `docs/` and returns citations with grounded answers.
- Tool-based actions: creates, reads, and updates marketing drafts, and can also run search, HTTP, and learning notes tools.
- Multi-step reasoning: uses LangGraph to move through router, planner, guardrail, retrieval, tool, and answer nodes.
- Guardrails: includes domain routing, tool/action allowlists, a max step limit, and direct fallback for unrelated questions.
- Observability: each request produces a `request_id`, metadata, `tool_trace[]`, and trace logs.

## Architecture

```text
Client
  |
  v
FastAPI app.py
  |-- GET  /
  |-- GET  /tools
  |-- POST /chat
  |-- POST /tools/{tool_name}
  |
  v
agent_graph.py
  |
  v
graphs/market_brain_graph.py
  |
  v
LangGraph StateGraph
  |
  |-- router_node      -> decides agent vs direct
  |-- direct_node      -> handles out-of-domain requests
  |-- planner_node     -> chooses retrieval, tool, or answer
  |-- guardrail_node   -> validates planner action
  |-- retrieval_node   -> retrieves document chunks from vector store
  |-- tool_node        -> selects and executes a registered tool
  |-- answer_node      -> generates final answer
  |
  v
ChatResponse
  |-- answer
  |-- metadata
  |-- tool_trace[]
  |-- citations[]
```

Main flow:

```text
router -> direct -> END
router -> planner -> guardrail -> retrieval -> planner
                              |-> tool      -> planner
                              |-> answer    -> END
```

## Repo Structure

```text
.
├── app.py
├── agent_graph.py
├── graphs/
├── nodes/
├── state/
├── chains/
├── rag/
├── tools/
├── services/
├── core/
├── memory/
├── docs/
├── scripts/
├── requirements.txt
├── build_index.py
├── db.py
└── schemas.py
```

### Top-level files

- `app.py`: the current FastAPI entrypoint. It registers `/chat`, `/tools`, and the healthcheck route, and initializes draft database tables on startup.
- `agent_graph.py`: a compatibility wrapper that exposes the `agent_graph` singleton and delegates the real implementation to `graphs/market_brain_graph.py`.
- `build_index.py`: loads documents from `docs/` and writes them into the PostgreSQL vector store.
- `db.py`: SQLAlchemy engine/session setup and initialization logic for `drafts`, `draft_versions`, and `draft_events`.
- `schemas.py`: Pydantic schemas for API requests and responses.
- `requirements.txt`: Python dependencies.

### `graphs/`

LangGraph workflow layer.

- `market_brain_graph.py` defines `MarketBrainGraph`.
- It creates `StateGraph(AgentState)` and registers nodes, conditional edges, loop edges, and terminal edges.
- It exposes `invoke(message, request_id, session_id)`, which returns a FastAPI-serializable result.

Typical changes:

- Add a new agent node.
- Adjust multi-step workflow order.
- Change max steps or routing edges.

### `nodes/`

Agent execution node layer. Each file usually maps to one LangGraph node.

- `router_node.py`: decides whether the request belongs to the Market Brain agent domain.
- `direct_node.py`: handles unrelated questions with a direct fallback response.
- `planner_node.py`: hybrid planner that uses rules first and falls back to an LLM for ambiguous cases.
- `guardrail_node.py`: validates whether the planner action is allowed and prevents duplicate or invalid actions.
- `retrieval_node.py`: calls the RAG retriever and produces `documents`, `retrieved_context`, and `citations`.
- `tool_node.py`: selects and executes a tool based on the user message.
- `answer_node.py`: combines retrieved docs and/or tool results to produce the final answer and metadata.

Typical changes:

- Tune planner rules.
- Change tool selection logic.
- Update answer-generation prompts or metadata.
- Strengthen guardrails.

### `state/`

LangGraph state definition layer.

- `agent_state.py` defines the shared `AgentState` fields passed between nodes.
- The graph and nodes rely on these field names to exchange context.

Typical changes:

- Add shared state required by a new node.
- Add intermediate results needed by response metadata.

### `chains/`

LLM chain composition layer.

- `rag_chain.py` builds the LangChain chain used for answer generation.
- `answer_node.py` calls this chain.

Typical changes:

- Replace the LLM chain structure.
- Adjust the base RAG answer prompt.
- Add a different model or parser.

### `rag/`

Document loading, splitting, indexing, and retrieval layer.

- `document_loader.py`: loads documents from `docs/`.
- `text_splitter.py`: chunks documents.
- `embedding_store.py`: OpenAI embeddings plus PostgreSQL vector store.
- `retriever.py`: wraps retrieval for `retrieval_node.py`.

Typical changes:

- Change document sources.
- Tune chunking strategy.
- Replace the vector store.
- Adjust `top_k` or retrieval result shape.

### `tools/`

Agent tool system.

- `base.py`: tool base class and `ToolResult`.
- `registry.py`: registers default tools and provides list/execute helpers.
- `draft_tool.py`: create/get/update draft tools.
- `http_tool.py`: HTTP request tool.
- `search_tool.py`: search tool.
- `learning_notes_tool.py`: learning notes example tool.

Typical changes:

- Add a new tool by implementing `BaseTool`, then register it in `build_default_registry()`.
- Adjust a tool's input validation or output shape.
- Extend what `/tools/{tool_name}` can execute.

### `services/`

Business service layer behind tools.

- `draft_service.py`: draft CRUD, version control, and event logging.

Typical changes:

- Change draft persistence behavior.
- Add business rules, audit records, or workspace isolation.
- Move complex tool logic into a service.

### `core/`

Cross-cutting infrastructure layer.

- `config.py`: environment variables and constants.
- `auth.py`: API key authentication.
- `logging.py`: structured logging.
- `tracing.py`: trace item builders and latency helpers.

Typical changes:

- Add new environment variables.
- Adjust authentication.
- Standardize logging or trace formats.

### `memory/`

Session memory layer.

- `session_store.py` is an example implementation for session-related context.
- The current main graph mostly passes through `session_id`; this layer can be expanded for short-term or long-term memory.

### `docs/`

RAG knowledge source files.

- Currently contains `return_policy.md`.
- After running `python build_index.py`, documents are written into the PostgreSQL vector store.

### `scripts/`

Development and smoke test scripts.

- `test_graph_smoke.py`: covers direct routing, router behavior, guardrail validation, state propagation, max steps, and API response shape.

## Setup

### 1. Create environment

```bash
python -m venv .venv
source .venv/bin/activate
make install
```

### 2. Configure environment variables

Create `.env`:

```bash
OPENAI_API_KEY=your_openai_api_key
APP_API_KEY=local-dev-key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=agent_platform
DB_USER=postgres
DB_PASSWORD=postgres
DB_SSLMODE=
DOCS_DIR=docs
EMBEDDING_MODEL_NAME=text-embedding-3-small
RAG_DB_HOST=localhost
RAG_DB_PORT=5432
RAG_DB_NAME=rag_db
RAG_DB_USER=postgres
RAG_DB_PASSWORD=postgres
RAG_DB_SSLMODE=
RAG_TABLE_NAME=documents
```

Notes:

- `/chat` and `/tools` are protected by `APP_API_KEY`.
- Draft persistence can use either `DATABASE_URL` or the `DB_*` variables above.
- The RAG vector store uses `RAG_DB_*` variables and defaults to database `rag_db`, table `documents`.
- For RDS, set `DB_SSLMODE=require` and `RAG_DB_SSLMODE=require` if your database requires SSL.

### 3. Prepare PostgreSQL

You need a local PostgreSQL instance and two databases:

```bash
createdb agent_platform
createdb rag_db
```

If you use Docker or a remote PostgreSQL instance, make sure the connection settings match `db.py` and `rag/embedding_store.py`.

## Docker

### Docker Compose

Run FastAPI and PostgreSQL together:

```bash
make compose-up
```

Equivalent command:

```bash
docker compose up --build
```

This starts:

- `app`: FastAPI on `http://127.0.0.1:8000`
- `postgres`: `pgvector/pgvector:pg16` with databases `agent_platform` and `rag_db`

The first Postgres startup runs `docker/postgres/init/01-create-databases.sql`, which creates the RAG database and enables the `vector` extension.

Stop the stack:

```bash
make compose-down
```

Tail logs:

```bash
make compose-logs
```

Build the RAG index inside the Compose network:

```bash
make compose-index
```

If you need to recreate the Postgres volume from scratch:

```bash
docker compose down -v
docker compose up --build
```

### Docker Image

Build the image:

```bash
docker build -t ai-agent-platform:local .
```

Run it locally against host PostgreSQL:

```bash
docker run --rm -p 8000:8000 \
  -e APP_API_KEY=local-dev-key \
  -e OPENAI_API_KEY=your_openai_api_key \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5432 \
  -e DB_NAME=agent_platform \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e RAG_DB_HOST=host.docker.internal \
  -e RAG_DB_PORT=5432 \
  -e RAG_DB_NAME=rag_db \
  -e RAG_DB_USER=postgres \
  -e RAG_DB_PASSWORD=postgres \
  ai-agent-platform:local
```

For ECS Fargate, push this image to Amazon ECR and configure the task definition with:

- Container port: `8000`
- Health check path on the ALB target group: `/`
- Environment variables: `ENVIRONMENT`, `APP_API_KEY`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_SSLMODE`, `RAG_DB_HOST`, `RAG_DB_PORT`, `RAG_DB_NAME`, `RAG_DB_USER`, `RAG_DB_SSLMODE`, `RAG_TABLE_NAME`
- Secrets Manager secrets: `OPENAI_API_KEY`, `DB_PASSWORD`, `RAG_DB_PASSWORD`
- RDS security group inbound rule allowing traffic from the ECS task security group on port `5432`

If the RDS instance was created without `--db-name`, use the default `postgres` database:

```text
DB_NAME=postgres
RAG_DB_NAME=postgres
```

That lets the app tables and RAG vector table live in the same RDS database. If you later create separate databases, set `DB_NAME` and `RAG_DB_NAME` to those names.

### 4. Build RAG index

```bash
make index
```

This command reads `docs/`, generates embeddings, and writes them into the PostgreSQL vector store.

### 5. Run API server

```bash
make dev
```

Default address:

```text
http://127.0.0.1:8000
```

You can override the host or port when needed:

```bash
make dev HOST=0.0.0.0 PORT=8080
```

## Usage

### Healthcheck

```bash
curl http://127.0.0.1:8000/
```

### List tools

```bash
curl \
  -H "x-api-key: local-dev-key" \
  http://127.0.0.1:8000/tools
```

### Chat

```bash
curl \
  -X POST http://127.0.0.1:8000/chat \
  -H "content-type: application/json" \
  -H "x-api-key: local-dev-key" \
  -d '{
    "message": "What is in the return policy?",
    "session_id": "demo-session"
  }'
```

Response shape:

```json
{
  "answer": "...",
  "metadata": {
    "request_id": "...",
    "model": "gpt-4o-mini",
    "route": "langgraph_hybrid_multistep_agent"
  },
  "tool_trace": [],
  "citations": []
}
```

### Execute a tool directly

```bash
curl \
  -X POST http://127.0.0.1:8000/tools/create_draft \
  -H "content-type: application/json" \
  -H "x-api-key: local-dev-key" \
  -d '{
    "content": "Launch email draft for Q4 campaign",
    "created_by": "user",
    "workspace_id": "default",
    "title": "Q4 Campaign"
  }'
```

## Development Guide

### Add a new tool

1. Create a new tool under `tools/` and inherit from `BaseTool`.
2. Implement `name`, `description`, and `run(tool_input)`.
3. Register it in `build_default_registry()` in `tools/registry.py`.
4. If the agent should select it automatically, update the selection rules in `nodes/tool_node.py` or introduce an LLM tool selector.

### Add a new graph node

1. Create a node function under `nodes/`.
2. If the node needs to pass data across the graph, update `state/agent_state.py`.
3. Register it with `add_node()` in `graphs/market_brain_graph.py`.
4. Add `add_edge()` or `add_conditional_edges()` based on the desired flow.
5. Update smoke tests to cover the new route.

### Add more RAG documents

1. Put Markdown or text files into `docs/`.
2. Run `python build_index.py`.
3. Ask questions through `/chat` and inspect returned `citations[]`.

### Change answer behavior

- For simple prompt changes, see `nodes/answer_node.py`.
- For chain structure changes, see `chains/rag_chain.py`.
- For retrieval context formatting, see `nodes/retrieval_node.py`.

## Testing

Smoke test:

```bash
python scripts/test_graph_smoke.py
```

Other test/evaluation entrypoints:

```bash
python test_auth.py
```

Some tests depend on:

- `OPENAI_API_KEY`
- local PostgreSQL
- a built RAG index
- initialized draft tables

## Current Main Path

The most important main path is:

```text
app.py
  -> agent_graph.py
  -> graphs/market_brain_graph.py
  -> nodes/router_node.py
  -> nodes/planner_node.py
  -> nodes/guardrail_node.py
  -> nodes/retrieval_node.py or nodes/tool_node.py
  -> nodes/answer_node.py
  -> schemas.ChatResponse
```

When reading or debugging the code, start with this path.
