# ADR 0003 — Alembic-only schema bootstrap

## Status

Accepted

## Context

`Container` previously called `Base.metadata.create_all()`, which hid missing
Alembic revisions (wardrobe tables, FTS5). Vertical-slice API tests passed while
a fresh `alembic upgrade head` environment would not.

## Decision

1. Normal bootstrap: `alembic upgrade head` → API / Worker start. No `create_all`.
2. `init_db()` remains for explicit unit-fixture use only and must stay in sync
   with migrations for any SQLite-native extras (FTS5).
3. Integration / E2E reset paths call `upgrade_head`, not `init_db`.

## Consequences

- Missing migrations fail loudly in new environments and in schema comparison tests.
- FTS5 (`marketplace_items_fts`) is created by migration 0003 and asserted in tests.
