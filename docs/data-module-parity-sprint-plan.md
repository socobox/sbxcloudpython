# Data Module Parity Sprint Plan

## Objective

Make the Bun Data module fully compatible with the old Node.js legacy implementation while also covering the Java backend's Data and SQL query capabilities, using the current Bun-native service architecture.

Primary implementation targets:

- Bun routes: `src/routes/data.ts`
- Bun services: `src/services/data.service.ts`, `src/services/query-engine.ts`, `src/services/query-executor.ts`
- Bun DB utilities: `src/db/*`
- Reference legacy implementation: `../legacy-sbxcloud/routes/data.js`, `../legacy-sbxcloud/service/data.js`
- Reference Java implementation: `../jsbx-backend/src/main/java/com/sbxcloud/sbx/controller/DataController.java`, `../jsbx-backend/src/main/java/com/sbxcloud/sbx/sql/*`

## Compatibility Principles

- Old Node is the behavioral compatibility baseline for existing clients.
- Java is the additive feature baseline for SQL query support and newer API behavior.
- Preserve legacy response shape unless a Bun-only endpoint is explicitly additive.
- Keep Bun-native APIs: `Bun.SQL`, Bun runtime, Hono routes, existing `routes -> services -> db` layering.
- Add focused tests before or alongside risky behavior changes.
- Do not "fix" legacy quirks unless the plan explicitly calls out an intentional compatibility exception.

## Current Status Summary

The Bun Data module has all old Node Data route shapes, but it is not yet behavior-compatible.

Known gaps:

- Missing legacy `require` and `geosort` query behavior.
- Partial `fetch`, nested fetch, `reverse_fetch`, and `reference_join` parity needs verification.
- Several Data mutations require only a token and do not enforce legacy domain access checks.
- Row insert/update silently skip unknown fields; legacy errors.
- Row insert does not create field rows for every model field.
- Sequence fields are not auto-filled when absent.
- `field/balance` behavior differs: legacy backfills missing rows, Bun returns a sum.
- `field/next` response shape differs.
- `row/model/list` ignores legacy `model` filter and weaker admin checks.
- `row/model/update` does not support the legacy `previous` request shape.
- Java SQL endpoints are missing entirely from Bun: `/api/sql/v1/query`, `/api/sql/v1/validate`, `/api/sql/v1/parse`.

## Sprint 0: Parity Harness And Fixtures

Goal: Create enough test infrastructure to safely compare Bun behavior against known legacy and Java semantics.

Tasks:

- Add a Data module parity test suite using `bun test`.
- Create deterministic DB fixtures for domains, apps, users, memberships, row models, field models, rows, references, sequence fields, and geo fields.
- Add helper factories for:
  - authenticated Hono requests
  - App-Key and Bearer token contexts
  - model creation and teardown
  - row assertions in EAV tables
- Capture current Bun behavior with regression tests before changing risky paths.
- Add a route inventory test that asserts all required Data routes and SQL routes exist.

Acceptance criteria:

- `bun test` runs real Data module tests instead of reporting "No tests found".
- Fixtures can create and reset a small EAV domain without depending on production data.
- The suite documents current failures as skipped or todo tests with clear issue names.

Deliverables:

- `src/**/*.test.ts` or `tests/data/*.test.ts`
- fixture utilities
- route coverage assertions

## Sprint 1: Access Control And Request Shape Parity

Goal: Match legacy authorization and input compatibility for all Data endpoints.

Tasks:

- Port or recreate legacy `grantDomainAccess` behavior for Data mutations and admin-only operations.
- Enforce domain membership/admin checks on:
  - `POST /api/data/v1/row`
  - `POST /api/data/v1/row/update`
  - `POST /api/data/v1/row/delete`
  - `POST /api/data/v1/row/truncate`
  - `GET /api/data/v1/row/model/list`
  - `POST /api/data/v1/row/model`
  - `POST /api/data/v1/row/model/update`
  - `DELETE /api/data/v1/row/model`
  - `POST|PUT|DELETE /api/data/v1/field/model`
  - `GET /api/data/v1/field/balance`
- Support legacy request aliases:
  - `row_model`, `model`, `row_model_id`
  - `field`, `field_id`
  - `previous` for row model rename
  - query-string and JSON-body variants where legacy accepted both.
- Review `requireToken` behavior against legacy missing-token and invalid-token responses.

Acceptance criteria:

- Unauthorized users cannot mutate or inspect admin-only model metadata for domains they do not manage.
- Existing legacy client request shapes work without client changes.
- Compatibility tests cover owner, developer, user, unrelated user, and dummy app contexts.

## Sprint 2: Row Insert, Update, Delete, And Sequence Semantics

Goal: Make row-level mutation match old Node EAV behavior.

Tasks:

- Change insert/update validation to error on unknown field names instead of silently skipping them.
- On row insert, create field rows for every field in the model, not just fields present in the payload.
- Preserve correct typed storage columns:
  - `string_value`
  - `text_value`
  - `numeric_value`
  - `date_value`
  - `boolean_value`
  - `reference_value`
- Auto-fill sequence fields when absent, matching legacy `field_sequence` behavior.
- Confirm required field behavior against legacy.
- Confirm `row.modification_time` updates on every mutation.
- Confirm delete behavior for single-key and multi-key payloads.
- Verify transaction boundaries and deadlock retry coverage.

Acceptance criteria:

- Inserted rows have one `field` row per `field_model`.
- Unknown fields return `{ success: false, error: ... }`.
- Sequence fields increment exactly once per inserted row.
- Delete and update behavior matches legacy response shape and side effects.

## Sprint 3: Query Engine Parity

Goal: Match legacy query behavior for `row/find`, `row/find/old`, and `row/find/pre`.

Tasks:

- Implement or confirm support for all legacy WHERE operators:
  - `=`, `!=`, `<>`, `>`, `<`, `>=`, `<=`
  - `LIKE`, `NOT LIKE`
  - `IN`, `NOT IN`
  - `IS NULL`, `IS NOT NULL`
  - date comparisons and relative time expressions
- Add legacy `require` query support.
- Add legacy `geosort` behavior or document and implement a compatible replacement.
- Verify pagination defaults:
  - `row/find`: default page size should match legacy behavior.
  - `row/find/old`: default size should be `1000`.
  - max page size remains `1000` unless legacy proves otherwise.
- Verify sort behavior, including metadata and field sorting.
- Verify `_KEY` and `_META` response format.
- Verify fetch behavior:
  - direct reference fetch
  - two-level fetch
  - missing reference rows
  - circular or repeated fetch protection
- Verify `reference_join` behavior.
- Decide whether `reverse_fetch` is Bun-only or should be harmonized with Java behavior.

Acceptance criteria:

- Legacy query fixtures return byte-for-byte compatible response structure where practical.
- Query tests cover every field type and operator.
- `require`, `fetch`, `reference_join`, and `geosort` have explicit passing tests or documented compatibility exceptions.

## Sprint 4: Model And Field Metadata Parity

Goal: Align row model and field model management with legacy and Java behavior.

Tasks:

- Add `model` filter support to `GET /api/data/v1/row/model/list`.
- Support legacy `POST /api/data/v1/row/model/update` request shape using `domain`, `name`, and `previous`.
- Confirm model creation returns the same identifiers and response keys expected by legacy clients.
- Confirm model delete cascades exactly as legacy expects.
- Align field model create/update/delete behavior:
  - type validation
  - reference model validation
  - label/required/array/sequence flags
  - duplicate field behavior
  - delete side effects on existing field rows
- Change `GET /api/data/v1/field/balance` to match legacy backfill behavior, or add a separate Bun-only endpoint for numeric summing if that feature is needed.
- Change `GET /api/data/v1/field/next` response shape to match legacy raw sequence response or add compatibility mode.

Acceptance criteria:

- Legacy metadata operations pass with the original query/body shapes.
- Field balance backfills missing field rows for all rows in the model.
- Sequence next endpoint returns a legacy-compatible payload.

## Sprint 5: Java SQL API On Bun

Goal: Implement Java's SQL query endpoints in Bun while compiling down to the Bun Data query engine.

Routes to add:

- `POST /api/sql/v1/query`
- `POST /api/sql/v1/validate`
- `POST /api/sql/v1/parse`

Tasks:

- Add `src/routes/sql.ts` and mount it from `src/app.ts`.
- Add SQL service modules:
  - `src/services/sql-syntax.ts`
  - `src/services/sql-schema.ts`
  - `src/services/sql-compiler.ts`
  - `src/services/sql.service.ts`
- Port Java-supported SQL features:
  - `SELECT * FROM model`
  - `WHERE` with supported operators
  - `AND`, `OR`, parentheses
  - `LIKE`
  - `IN`, `NOT IN`
  - `IS NULL`, `IS NOT NULL`
  - `BETWEEN`
  - `LIMIT`, `OFFSET`
  - dot notation for reference fields, e.g. `CUSTOMER.NAME`
- Reject unsupported SQL with clear errors:
  - selected columns other than `*`
  - `ORDER BY` if not intentionally supported
  - `GROUP BY`, `HAVING`
  - joins
  - subqueries
  - unions
- Compile valid SQL into existing `find()` requests.
- Return Java-compatible metadata:
  - `_sql.original`
  - `_sql.compiled`
  - `_sql.timing_ms`
- Require auth for query and validate; allow unauthenticated parse if Java parity requires it.

Acceptance criteria:

- Java SQL examples work against Bun.
- Invalid SQL returns phase-specific errors: syntax, schema, compile, execution.
- SQL endpoints share the same Data authorization rules as native Data queries.

## Sprint 6: Performance, Safety, And Observability

Goal: Keep the compatible implementation production-safe under Bun.

Tasks:

- Review query plans for common EAV operations.
- Add bounded concurrency for fetch/reference expansion where needed.
- Ensure large `IN` clauses are chunked or bounded.
- Add request logs for expensive Data queries with request ID, domain, model, size, and duration.
- Add defensive limits for:
  - fetch depth
  - row count
  - SQL parse size
  - geosort result size
- Revisit `MAX_BODY_SIZE_BYTES`; legacy allowed `250mb`, current Bun default is 2 MiB.
- Add compatibility notes to `CLAUDE.md` after implementation.

Acceptance criteria:

- Data tests pass under normal and large fixture sets.
- Type check passes with `bun run check`.
- Query latency and error logs include enough metadata to diagnose production issues.

## Final Acceptance Checklist

- All old Node Data endpoints exist and pass compatibility tests.
- All old Node Data request shapes used by client libraries are accepted.
- All old Node Data mutation side effects are reproduced.
- All Java Data endpoints remain covered.
- Java SQL endpoints are implemented on Bun.
- `bun run check` passes.
- `bun test` passes.
- Manual smoke tests pass against a MySQL fixture database.
- Any intentional compatibility exception is documented with reason, affected clients, and migration path.

## Suggested Sprint Order

1. Sprint 0: test harness and fixtures.
2. Sprint 1: authorization and request shape parity.
3. Sprint 2: row mutation and sequence semantics.
4. Sprint 3: query engine parity.
5. Sprint 4: metadata endpoints.
6. Sprint 5: Java SQL API.
7. Sprint 6: performance and production hardening.

## Open Questions

- Should Bun preserve old Node bugs exactly when Java corrected them?
- Should `reverse_fetch` remain Bun-only, or should it be exposed/documented as part of the Java-compatible Data API?
- Should `field/balance` keep Bun's current numeric-sum behavior under a new endpoint before restoring legacy backfill behavior?
- Which client libraries are authoritative for request shape: Java client, Python client, TypeScript client, or captured production traffic?
- Is Push/Payment style "Phase 6" work out of scope for Data parity, or should cross-module app/domain config behavior be fixed at the same time?
