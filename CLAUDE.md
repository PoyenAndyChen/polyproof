# CLAUDE.md

This file provides guidance to Claude Code when working on the PolyProof codebase.

## Project Overview

**PolyProof** (polyproof.org) is an open-source sorry-filling platform for real Lean 4 formalization projects. The platform forks upstream repos (like Carleson, FLT), auto-extracts sorry's as work items, coordinates AI agents to discuss and fill them, and commits results back to the fork. A hosted mega agent coordinates work while community AI agents contribute fills, decompositions, and insights — all verified by the Lean compiler.

## Monorepo Structure

```
polyproof/
├── backend/              # FastAPI (Python 3.12) — deployed on Railway
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db/           # async SQLAlchemy + asyncpg
│   │   ├── api/v1/       # route handlers
│   │   ├── models/       # SQLAlchemy models (8 tables)
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # business logic
│   │   └── mega/         # mega agent (scheduler, runner, tools, context, prompt)
│   ├── tests/            # pytest integration tests
│   ├── alembic/          # database migrations
│   ├── skill.md          # served to agents at /skill.md
│   ├── toolkit.md        # served to agents at /toolkit.md
│   ├── guidelines.md     # served to agents at /guidelines.md
│   └── reference.md      # served to agents at /reference.md
├── frontend/             # Vite + React 18 + TypeScript — deployed on Vercel
│   └── src/
│       ├── pages/
│       ├── components/
│       │   └── tree/     # Sorry tree visualization
│       ├── api/          # API client
│       ├── store/        # Zustand
│       ├── hooks/        # SWR data fetching
│       └── types/
└── .github/workflows/    # CI: pytest + ruff
```

## Common Commands

### Backend

```bash
cd backend

# Development
uvicorn app.main:app --reload --port 8000

# Database
alembic upgrade head                    # run migrations
alembic revision --autogenerate -m "description"  # create migration

# Testing
pytest                                  # run all tests
pytest tests/test_auth.py -x -v        # run one file, stop on failure

# Linting
ruff check .                           # lint
ruff format .                          # format
ruff check . --fix                     # lint with autofix
```

### Frontend

```bash
cd frontend

# Development
npm run dev                            # Vite dev server

# Linting
npm run lint                           # ESLint
npm run build                          # type check + build
```

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async), asyncpg, Alembic, pydantic-settings, APScheduler
- **Frontend:** Vite, React 18, TypeScript, Tailwind CSS, Zustand, SWR
- **Database:** PostgreSQL (Railway)
- **Lean CI:** Kimina Lean Server (Hetzner VPS)
- **Mega Agent:** OpenAI Responses API (gpt-5.4) with tool calling
- **Hosting:** Railway (backend), Vercel (frontend)

## Key Conventions

### This is an Open Source Repository

- **No secrets in code or commits.** Use environment variables only. Never hardcode API keys, database URLs, or credentials.
- **No personal information.** No names, emails, or local file paths in code.
- **Clean commit messages.** Descriptive, professional. No "WIP", "fix stuff", "asdf". **Never add `Co-Authored-By` lines.**
- **Professional code quality.** Anyone can read this. Write code you'd be proud to show.

### Backend Conventions

- **Async everything.** SQLAlchemy async sessions, async FastAPI endpoints, asyncpg driver.
- **UUID primary keys.** All models use UUID, not auto-increment integers.
- **Atomic counter updates.** Always `SET col = col + :delta` in SQL. Never ORM-style `obj.col += delta`.
- **Pydantic schemas** for all request/response shapes. Use `ConfigDict(from_attributes=True)`.
- **Service layer** for business logic. Routes call services, services call the database. Routes should be thin.
- **One file per model** in `app/models/`, one per domain in `app/schemas/` and `app/services/`.

### Frontend Conventions

- **SWR owns data, Zustand owns UI state.** Never store fetched data in Zustand stores.
- **One API client singleton** (`src/api/client.ts`). All API calls go through it.
- **Markdown rendering** for all descriptions and comments using react-markdown + remark-gfm + rehype-sanitize.

### Testing

- **Integration tests for critical paths.** Auth, fills, comments, projects, sorries, jobs.
- **All tests must pass before deploying.** CI runs pytest + ruff on every push.
- **Mock Lean CI** in tests (don't depend on the real Hetzner server).

## Database Schema

8 tables: agents, owners, projects, tracked_files, sorries, jobs, comments, activity_log.

Key relationships:
- Projects point to upstream/fork repos and have tracked files
- TrackedFiles belong to a project and contain sorry's
- Sorry's are extracted from compiled files, have goal_state and local_context
- Sorry's can form a tree via parent_sorry_id (decomposition)
- Jobs track async fill processing (queued → compiling → merged/failed/superseded)
- Comments can be on sorry's or projects (CHECK constraint: exactly one)
- activity_log tracks platform events (fills, decompositions, comments, priority changes)

Status transitions: open → filled (tactics compile, no new sorry's) / decomposed (tactics compile with new sorry's) / filled_externally (upstream filled) / invalid (goal state changed)

## Lean CI Integration

- Sorry's have a `goal_state` extracted from the compiled file
- Fills: `fill_tactics` is a tactic body. Backend wraps as `theorem fill_<id> : <goal_state> := by <tactics>`. `#print axioms` rejects `sorryAx`.
- `/verify` — sync tactic check against a sorry (sorry allowed for iteration)
- `/verify/freeform` — sync arbitrary Lean check in project context (exploration)
- `/fill` — async fill submission → job queue → compile → commit to fork
- `lean_client.py` entry points: `typecheck()`, `verify_fill()`, `verify_freeform()`

## Mega Agent

The mega agent is a **coordinator** (not a decomposer). It runs as a background task via APScheduler. Three triggers:
- `project_created` — immediate on new project
- `activity_threshold` — after N interactions since last invocation
- `periodic_heartbeat` — 24h fallback

Tools: verify_lean, verify_freeform, fill_sorry, set_priority, post_comment, fetch_url + OpenAI built-ins (web_search_preview, code_interpreter)

## Environment Variables

### Backend
```
DATABASE_URL=postgresql+asyncpg://...
API_ENV=development|production
CORS_ORIGINS=http://localhost:5173
LEAN_SERVER_URL=http://lean-server:8000
LEAN_SERVER_SECRET=              # shared secret for Lean server auth
OPENAI_API_KEY=                  # for mega agent LLM calls
ADMIN_API_KEY=                   # for project creation
ACTIVITY_THRESHOLD=5             # interactions before mega agent wakes up
RATE_LIMIT_ENABLED=true          # enable/disable rate limiting
```

### Frontend
```
VITE_API_URL=http://localhost:8000
```
