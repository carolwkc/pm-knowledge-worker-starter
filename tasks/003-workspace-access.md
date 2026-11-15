# Task 003 — Authenticated workspace access

## Outcome

Require operator-issued bearer credentials and workspace membership throughout the
existing source-to-answer API. Readers search/ask, editors also upload/version,
and owners also administer memberships. Every source shares workspace access.

## Implementation sequence

1. Add migration `0003` for users, hashed/expiring/revocable tokens and unique,
   role-constrained memberships. Preserve all existing evidence and embeddings.
2. Add trusted operator commands to create users, issue/revoke tokens and explicitly
   assign legacy workspace owners. Tokens use 32 random bytes and default to 30 days;
   plaintext is emitted only once, after successful commit.
3. Enforce bearer authentication on all `/api/v1` routes; expose current identity,
   joined workspace listing and owner-only membership administration. Workspace
   creation atomically grants ownership. Keep health/schema/docs public.
4. Pass identity into ingestion/search/ask, checking roles before processing/inference.
   Include membership and workspace/latest-version predicates in both SQL retrievers
   before ranking/limits. Keep backfill privileged and evaluation fixtures temporary.
5. Serialize membership writes with a workspace lock, recheck the actor after locking,
   and reject final-owner removal/demotion. Apply revocations on subsequent requests.
6. Exercise actual issued credentials, both SQL retrievers, concurrent mutations,
   migration compatibility, original provenance and Docker HTTP operation. Update
   setup, contracts and verification; request review before Task 004.

## Acceptance and defaults

- Missing/invalid/expired/revoked credentials: 401 plus Bearer challenge.
- Missing or inaccessible workspace: indistinguishable 404; insufficient role: 403.
- Unknown membership/user: 404; final-owner removal/demotion: 409.
- No default token, implicit legacy membership or authentication bypass.
- No plaintext tokens in persistence, application logs or error responses.
- Existing content/version/citation semantics remain covered by integration tests.
- No document ACLs, password login, SSO, frontend or production deployment work.
- CLI access remains a trusted database-operator privilege. In-flight requests may finish.

The approved implementation request is the specification. Verification and limitations
are recorded in [Task 003](../docs/TASK_003.md). Do not commit without an explicit request.
