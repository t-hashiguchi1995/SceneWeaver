# ADR 0005 — CSP Handoff from adopted Asset bytes

## Status

Accepted (MVP Hardening #5)

## Context

Earlier handoff wrote empty placeholder PNGs, so vertical-slice success did not
prove Review → CSP data flow.

## Decision

1. Handoff resolves each panel `asset_id` via AssetRepository + AssetStore.
2. Only `review_decision=adopted` assets are eligible; rejected/pending fail the whole handoff.
3. Bytes are copied to `panel_*_clean.png`; output sha256 must equal Asset.sha256.
4. Manifest records `asset_id`, `sha256`, `shot_id`, `panel_slot_id`, `script_event_ids`.
5. Revisions are immutable (`r001`, `r002`, …); reusing an existing revision fails.

## Consequences

- Placeholder PNG generation is removed.
- Playwright E2E can assert real panel bytes and manifest hashes.
