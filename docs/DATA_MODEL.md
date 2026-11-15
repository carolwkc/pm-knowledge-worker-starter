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

## Later knowledge entities

strategy, customer, insight, opportunity, initiative, decision, evidence, competitor, entity_relation, review_event.

Each derived assertion should point to one or more immutable evidence spans with extraction model/version and review status. Preserve revisions and supersession, do not silently overwrite history.
