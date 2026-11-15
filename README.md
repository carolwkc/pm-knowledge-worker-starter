# PM Knowledge Worker

An evidence-first, team-oriented Product Knowledge System with an AI assistant.

## Goal

Help product managers, designers, and engineering leads answer: What do we know? Where did we learn it? What have we decided? Why? What does it mean next?

## First milestone — Knowledge Foundation

1. Ingest sample product documents (Markdown/text first).
2. Persist original sources, document versions, chunks, and provenance.
3. Search documents through keyword search (semantic retrieval may follow).
4. Ask questions through a simple API and return source-grounded answers with citations.
5. Run locally using Docker Compose and test with fixture data.

The first milestone **does not** include autonomous agents, roadmaps, Slack, CRM, product analytics, or production SSO.

## Proposed stack

- Backend: Python 3.12+, FastAPI, SQLAlchemy, Alembic, pytest
- Data: PostgreSQL 16+, pgvector when semantic search is introduced
- Frontend: Next.js and TypeScript (after backend vertical slice)
- AI: provider abstraction; external API calls optional in initial tests
- Local environment: Docker Compose

Dependencies and exact versions should be selected and pinned by Codex after checking compatibility.

## Getting started with Codex

Open this directory in Codex (desktop or CLI). Codex will read `AGENTS.md` for project guidance.

First prompt:

> Read AGENTS.md, docs/PRODUCT.md, docs/ARCHITECTURE.md and tasks/001-knowledge-foundation.md. Produce a short implementation plan, then implement Task 001 as a minimal working, tested vertical slice. Keep the scope narrow. Use synthetic fixtures, no secrets, and no external integrations. Run tests and document commands/results. Do not start later phases.

## Documents

- `AGENTS.md` — Codex project instructions
- `PLANS.md` — delivery milestones and working practices
- `docs/PRODUCT.md` — product scope and acceptance criteria
- `docs/ARCHITECTURE.md` — target design and data flows
- `docs/DATA_MODEL.md` — initial entities and provenance contract
- `tasks/001-knowledge-foundation.md` — first implementation task

## Security

No actual company, customer, interview, or employee data should enter the repository. Use generated fixtures until source permissions, data handling, and retention requirements are established.
