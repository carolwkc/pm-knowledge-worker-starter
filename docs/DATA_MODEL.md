# Initial data model and provenance

## Core tables for Task 001

### workspace
- id (UUID, primary key)
- name
- created_at

### source_document
- id (UUID, primary key)
- workspace_id (FK)
- title
- source_type (upload, future: drive/notion/...)
- external_uri (nullable)
- created_at

### document_version
- id (UUID, primary key)
- source_document_id (FK)
- version_number
- sha256
- plain_text
- ingested_at
- unique (source_document_id, sha256)

### source_chunk
- id (UUID, primary key)
- document_version_id (FK)
- ordinal
- text
- start_char / end_char
- unique (document_version_id, ordinal)

All retrieval joins must be scoped by workspace_id. Use migrations and explicit indexes.

### Task 001 persistence details

- UUIDs are generated once on insert. All timestamps use timezone-aware PostgreSQL types.
- Version numbers are positive and unique per source in addition to the hash constraint.
  Uploads lock the source row before checking either value.
- `plain_text` stores the original valid UTF-8 contents, including Markdown syntax,
  Unicode and CRLF line endings. SHA-256 is over the uploaded bytes without normalization.
- Chunks use zero-based ordinals and end-exclusive Unicode character offsets;
  `plain_text[start_char:end_char] == text`. Paragraphs are kept separate and split at
  whitespace if over 1,000 characters. Long unbroken tokens split at the limit.
- `source_chunk.search_vector` is a generated English `tsvector` with a GIN index.
  The workspace foreign key is indexed; unique version/chunk indexes also serve their
  foreign-key joins. Check constraints validate ordinal and span lengths.
- Parent foreign keys cascade on deletion. The Task 001 API exposes append operations
  only; it has no mutation/deletion endpoint for existing text, chunks, or metadata.
  Immutability is an API guarantee, not a database role/trigger restriction.
- Search excludes superseded versions, but their text and stable evidence IDs remain
  stored. Source UUID, version UUID, chunk UUID and offsets identify each citation.

## Answer contract example

```json
{
  "answer": "The decision prioritised troubleshooting speed [1].",
  "status": "grounded",
  "sources": [
    {
      "citation": "1",
      "source_document_id": "uuid",
      "document_version_id": "uuid",
      "chunk_id": "uuid",
      "title": "Observability decisions",
      "excerpt": "We prioritise troubleshooting speed in Release 1.",
      "start_char": 0,
      "end_char": 49
    }
  ]
}
```

Without a configured model, a deterministic extractive response is acceptable; do not imply that it has performed reasoning.

## Task 002 derived embeddings

`chunk_embedding` stores `chunk_id` (FK with cascade), `model_id`, and a 384-dimensional
pgvector `embedding`. The chunk/model pair is the primary key; repeated ingestion
and backfill use conflict-safe inserts. Embeddings are derived data and never replace
source text or offsets. Current local encoder: `BAAI/bge-small-en-v1.5` via FastEmbed.

Both vector and keyword queries join through the version and source document to
filter by workspace and exclude superseded versions before ranking. Backfill only
selects missing vectors for latest versions in an explicitly requested workspace.
Inference/inserts run in batches of 64 within the caller's transaction; failures
roll back the whole ingestion/backfill. Exact cosine search is used at this scale;
there is no approximate index or independent vector service.

## Task 003 identities and workspace permissions

- `app_user`: stable UUID, display `name`, timezone-aware `created_at`. Display names
  are not login credentials and need not be unique.
- `api_token`: UUID, indexed user FK, unique 64-character SHA-256 `token_hash`,
  `created_at`, mandatory `expires_at`, optional `revoked_at`. No plaintext secret is
  stored. User deletion cascades to tokens.
- `workspace_membership`: composite primary key `(workspace_id, user_id)`, indexed
  user FK, and a check-constrained `reader|editor|owner` role. Parent deletion cascades
  memberships. The API prevents removing/demoting the last owner under a workspace
  row lock; this is an application invariant, not a database aggregate constraint.

Migration `0003` adds these tables only. No source evidence or embeddings are rewritten,
and legacy workspaces receive no implicit owner. The trusted operator CLI assigns
owners explicitly. New API-created workspaces commit their first owner atomically.

Both retrieval queries require membership via SQL `EXISTS` before ranking and limits,
as well as the existing workspace/latest-version predicates. HTTP service entrypoints
also check the required role before document processing or inference. Memberships
and tokens are checked afresh each request; there are no permission/answer caches.

## Later knowledge entities

strategy, customer, insight, opportunity, initiative, decision, evidence, competitor, entity_relation, review_event.

Each derived assertion should point to one or more immutable evidence spans with extraction model/version and review status. Preserve revisions and supersession, do not silently overwrite history.
