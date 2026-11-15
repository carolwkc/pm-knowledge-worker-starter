# Task 009 — Q&A feedback and owner inspection

## Delivered

Members explicitly save Helpful/Not helpful opinions with optional negative reason
and comment. Saved context contains the submitted question/mode and displayed answer,
even after the question draft changes. Ordinary ask calls still save nothing.
Owners inspect paginated/filterable summaries and user-reported detail with exact
original-version citation navigation. Historical evidence remains pinned.

Migration `0005` introduces a separate workspace-scoped `answer_feedback` table.
Source joins check citation identity, text, metadata and offsets before persistence;
the shared pure quotation formatter checks answer/status formatting. This establishes
citation integrity, not proof the API returned that answer for that question.
Authenticated attribution and an atomic workspace/author/submission uniqueness
constraint make identical normalized retries return the original receipt and changed
payloads conflict. No client-provided actor establishes identity.

Browser state stays in memory. Unsent forms clear on view changes; saved/uncertain
submissions stay with the completed answer within its workspace. Scope/session/access
changes and new questions clear it. Uncertain writes freeze their body/UUID and require
an explicit Retry; navigation abort does not guarantee server rollback. No automatic
write retry, decision publication or source mutation is introduced.

Specification: [Task 009](../tasks/009-answer-feedback.md).
Walkthrough and commands: [README](../README.md#task-009-submit-and-inspect-qa-feedback).

## Verification

Verification uses locked dependencies, Python 3.12.12, Node 25.2.1 and a dedicated
Compose project `dakar-task009`: PostgreSQL port 55439, API port 58009 and database
`pmknowledge_test`. Existing projects, volumes and `.env` files are unchanged.

Initial red runs: all 18 backend feedback cases failed on missing endpoints; all 12
initial component cases failed on missing feedback controls. Implementation made them
pass. Further cases cover bounds, ordinary-query non-persistence, revoked credentials,
owner demotion, migration preservation, malformed receipts and navigation uncertainty.
One test assertion incorrectly matched the word “inputs” in a validation message;
it was corrected to check that validation objects omit their submitted input field.
Typechecking also caught unsupported Testing Library `exact` options on role queries;
these were removed. Formatting issues were corrected with the configured formatters.

Executed on 2026-11-15:

| Check | Result |
| --- | --- |
| `uv sync --dev --frozen`, web `npm ci` | Passed |
| Dedicated-database `uv run pytest -q` | 179 passed |
| `uv run ruff check .`, `uv run ruff format --check .` | Passed |
| `uv run mypy apps/api/src` | Passed, 15 source files |
| Web `npm test` | 135 passed: 119 prior and 16 feedback tests |
| Web `typecheck`, `lint`, `format:check`, `build` | Passed |
| Dedicated-database `uv run alembic check` | No new upgrade operations |
| Docker build and health | Passed |
| Real HTTP Chromium integration | 11 passed, including initial-navigation demotion |
| Synthetic browser fixture cleanup | Zero remaining users/workspaces/feedback rows |
| Runtime UID | 10001 |
| `git diff --check` | Passed |

API coverage additionally exercises concurrent differing valid payloads using one
submission UUID: exactly one saves and the other conflicts. After privileged source
removal, detail retains the saved context, identical replay returns its receipt and
original-source reads safely return 404. Migration round trips preserve sources,
embeddings, memberships, credentials, proposals, reviews and decisions.

The real-browser walkthrough covers reader submission after a source update, edited
question/mode isolation, explicit keyboard submission at 390px, owner inspection,
historical verified highlights, inert markup/URI metadata, memory-only browser
storage and insufficient-evidence feedback. All nine previous browser regressions
remain intact. The synthetic owner view screenshot was captured and visually
inspected at `.context/feedback.png`. The existing NO_COLOR/FORCE_COLOR warning is
unchanged and does not indicate a test failure.

## Changed files

- Backend: feedback service, strict schemas, SQLAlchemy model, three API routes,
  shared quotation composer and migration `0005_answer_feedback.py`.
- Browser: feedback form/browser/state modules, typed transport and integration with
  App/navigation, knowledge state and existing styles.
- Verification: API/concurrency/retention and migration tests, feedback component tests
  and two additional real-browser scenarios.
- Documentation: Task 009 specification/verification, README, delivery plan,
  architecture and data model.

## Independent review

A fresh read-only reviewer inspected all tracked/untracked changes against the task
specification. They found one P2: an owner demoted before initial Feedback navigation
could retain the empty owner view because access-refresh routing used the previous
render's view. A regression test failed before the fix; routing now checks the active
state, and the complete 135-test web suite passes. Existing proposal access-refresh
routing uses the same correction. The reviewer found no other actionable defects.

The reviewer noted concurrency/retention coverage gaps; both received the API tests
described above. They did not run tests themselves. Production operational readiness,
comprehensive accessibility and cross-browser behavior remain explicitly outside this
local synthetic-data slice; no such readiness claim is made.

## Limitations and operation

- Feedback is user opinion with user-reported context, never authoritative knowledge
  or a verified query log. Missing-evidence reports are not re-run against later content.
- Snapshots persist until workspace deletion, including after privileged source
  removal; there is no editing, deletion, resolution, analytics or retention-management
  API/UI. Original reads fail safely if source rows are unavailable. Author FKs preserve
  attribution and prevent deleting referenced users.
- One receipt per completed answer is a tab-level UI rule. A caller can deliberately
  create another report with another UUID; there is no global one-vote-per-question rule.
- Pagination/freshness are read-time snapshots. Permission changes affect subsequent
  requests; already running requests may finish. Browser data clears when access loss
  is detected or the scope/session is cleared. Reload loses pending retry context.
- Tests use synthetic content only. Chromium/keyboard/narrow-viewport coverage does
  not establish full cross-browser or assistive-technology conformance.
- No dependencies, models, integrations, external writes, commits or branch rename.

The dedicated API is at `http://127.0.0.1:58009`. Stop only this project and retain
its volumes using:

```sh
POSTGRES_PASSWORD=localdev POSTGRES_PORT=55439 API_PORT=58009 \
  docker compose -p dakar-task009 -f compose.yaml -f apps/web/e2e/compose.yaml down
```
