# Findings & Decisions

## Requirements
- User first said "auth", then explicitly requested use of the planning-with-files skill.
- No concrete auth outcome was initially specified; after the stop hook requested continuation, proceed with a conservative API-key auth implementation.
- Planning files must live in the project root: task_plan.md, findings.md, and progress.md.

## Research Findings
- Planning-with-files skill requires a session catchup check before work.
- Session catchup helper produced no output on 2026-04-28, so there was no reported unsynced context.
- Project root currently contains Python app files and directories including api, core, services, db.py, app.py, and requirements.txt.
- No application authentication or authorization implementation was found in active code during the initial scan.
- `app.py` is the only file that instantiates `FastAPI` and exposes active routes: `GET /`, `GET /tools`, `POST /chat`, and `POST /tools/{tool_name}`.
- `app.py` does not use FastAPI dependencies, security schemes, middleware, cookies, headers, bearer tokens, or API keys for inbound requests.
- `schemas.ChatRequest` accepts `message` and optional `session_id`; `session_id` is conversational memory context, not authentication.
- `requirements.txt` does not include common auth libraries such as `python-jose`, `PyJWT`, `passlib`, or FastAPI auth helpers.
- `api/routes/chat.py` defines an `APIRouter`, but no code imports or includes it. It also references `core.config.settings`, `ChatMetadata`, and `request.stream`, which do not exist in the files inspected, so it appears stale or unused.
- The draft persistence schema has actor/workspace fields (`created_by`, `updated_by`, `workspace_id`) but no user table, role table, credentials table, or ownership checks.
- `core.config` reads `OPENAI_API_KEY` for outbound OpenAI calls; this is not inbound user authentication.
- `db.py` defaults `DATABASE_URL` to local Postgres credentials and creates draft-related tables on startup.
- Implemented inbound API-key auth for active capability endpoints using `X-API-Key`.
- `GET /` remains public.
- Protected endpoints fail closed with HTTP 503 when `APP_API_KEY` is not configured.
- Protected endpoints return HTTP 401 for missing or invalid `X-API-Key`.
- Focused auth tests pass using standard-library `unittest`.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Treat "auth" as an auth workstream until clarified | The single-word request is too broad to safely implement a specific flow. |
| Discover existing implementation before proposing code changes | Existing routes, dependencies, and storage patterns should drive the implementation. |
| Use environment variable `APP_API_KEY` for inbound API key auth | Matches existing config style and avoids database/user-model work. |
| Accept API key through `X-API-Key` header | Simple, explicit, and easy to test with FastAPI's APIKeyHeader. |
| Fail closed when `APP_API_KEY` is unset | Avoid accidentally exposing protected endpoints in deployed environments. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Project environment does not have pytest installed | Converted focused auth tests to standard-library unittest. |
| Existing broader unittest discovery fails outside auth | Logged unrelated failures in `test_day5_chunking` and `test_day7_retriever`; did not change unrelated test targets. |

## Resources
- Skill instructions: /Users/tianfeng/.codex/skills/planning-with-files/SKILL.md
- Project root: /Users/tianfeng/ai-agent-platform
- Active app entrypoint: /Users/tianfeng/ai-agent-platform/app.py
- Request/response schemas: /Users/tianfeng/ai-agent-platform/schemas.py
- Config: /Users/tianfeng/ai-agent-platform/core/config.py
- Database setup: /Users/tianfeng/ai-agent-platform/db.py
- Potentially stale router: /Users/tianfeng/ai-agent-platform/api/routes/chat.py
- Auth dependency: /Users/tianfeng/ai-agent-platform/core/auth.py
- Auth tests: /Users/tianfeng/ai-agent-platform/test_auth.py

## Visual/Browser Findings
- None.

---
*Update this file after every 2 view/browser/search operations.*
