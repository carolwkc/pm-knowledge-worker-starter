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
