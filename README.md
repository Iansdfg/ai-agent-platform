# AI Agent Platform (Market Brain Agent)

A production-style AI Agent Platform built with:

- FastAPI (API layer)
- LangGraph (agent orchestration)
- RAG (retrieval + grounding)
- Tool system (draft / search / HTTP)
- PostgreSQL + pgvector (vector store)
- OpenAI / LangChain (LLM layer)
- Structured tracing + observability

---

## 🚀 Project Overview

This project simulates a real-world **AI Marketing Agent (Market Brain)** that can:

### Core Capabilities

1. **RAG-based Q&A**
   - Retrieve knowledge from documents
   - Ground answers with citations

2. **Tool-based Actions**
   - Create / get / update marketing drafts
   - Call external APIs (HTTP tool)
   - Search internal data

3. **Multi-step Agent Reasoning**
   - Planner decides next action
   - Supports:
     - retrieval → answer
     - tool → answer
     - multi-step loops

4. **Guardrails (partial)**
   - Max step limit
   - Tool allowlist
   - Direct fallback for unrelated queries

---

## 🧠 Architecture

```text
Client
  ↓
FastAPI (/chat)
  ↓
LangGraph Agent

[Router]
  → direct (guardrail)
  → agent

[Planner]
  → retrieval
  → tool
  → answer

[Nodes]
  → Retriever (RAG)
  → Tool execution
  → Answer generation

[Output]
  → answer
  → metadata
  → tool_trace[]
  → citations[]