# Task Plan: Auth Work

## Goal
Determine the repository's current authentication surface, clarify the requested auth outcome, and implement the smallest correct change once requirements are concrete.

## Current Phase
Phase 5

## Phases

### Phase 1: Requirements & Discovery
- [x] Identify existing auth-related files, routes, middleware, configuration, and dependencies.
- [x] Document the current auth behavior and any gaps in findings.md.
- [x] Confirm the exact desired auth change if it cannot be inferred safely from the codebase.
- **Status:** complete

### Phase 2: Technical Plan
- [x] Decide where the auth change belongs based on existing project structure.
- [x] Define the minimum viable implementation and verification path.
- [x] Document decisions and rationale.
- **Status:** complete

### Phase 3: Implementation
- [x] Apply targeted code changes.
- [x] Preserve unrelated user changes in the worktree.
- [x] Update planning files as discoveries and decisions are made.
- **Status:** complete

### Phase 4: Testing & Verification
- [x] Run the relevant tests or smoke checks.
- [x] Fix issues found during verification.
- [x] Record results in progress.md.
- **Status:** complete

### Phase 5: Delivery
- [x] Review touched files and summarize behavior.
- [x] Note any remaining risks, manual setup, or follow-up work.
- [x] Deliver concise handoff to the user.
- **Status:** complete

## Key Questions
1. What does "auth" mean for this request: inspection, bug fix, adding login, API protection, token validation, or another flow?
2. Does the project already have an auth model, dependency, middleware, or database schema to extend?
3. What tests or manual checks prove the auth behavior works?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use file-based planning before further auth work | The user explicitly requested the planning-with-files skill. |
| Start with discovery before implementation | The user only said "auth", so implementation requirements are not yet concrete. |
| Pause before implementing auth mechanism | The repository has no current inbound auth pattern, so choosing JWT/session/OAuth/API-key auth needs product direction. |
| Implement simple API-key auth | The user prompted continuation after the stop hook; API-key auth is the smallest useful inbound auth mechanism that needs no new dependencies or data model. |
| Keep `GET /` public | Health checks should remain usable without credentials. |
| Protect `GET /tools`, `POST /chat`, and `POST /tools/{tool_name}` | These are the active application endpoints that expose capabilities or invoke the agent/tool registry. |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `pytest` command not found | 1 | Check project virtualenv or alternate test invocation. |
| `python -m pytest test_auth.py` failed because pytest is not installed | 2 | Convert focused tests to standard-library unittest. |
| `unittest discover` failed in pre-existing tests | 3 | Record as unrelated: `test_day5_chunking` cannot import `Document`; `test_day7_retriever` uses an outdated `Retriever` constructor call. |

## Notes
- Update phase status as work progresses.
- Re-read this plan before major decisions.
- Log all errors and avoid repeating failed actions unchanged.
