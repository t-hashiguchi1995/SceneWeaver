# ADR 0008 — Applicationization Phase (v0.2) / Sprint 1 shell

## Status

Accepted

## Context

MVP v1.0 (`v0.1.0`) proved the Domain→Application→Ports→Adapters path end-to-end.
Creators still need `.env`, terminals, and README knowledge to start work.

## Decision

Ship **v0.2 Applicationization** in sprints. Sprint 1 = Application Shell & Setup:

1. Setup Wizard + Settings UI (workspace, Comfy, LLM, Eagle optional, CSP export dir)
2. Integration Hub with Comfy **Diagnose Environment**
3. Recent Projects + Character Library entry points
4. `sceneweaver start` launcher (API + Worker + Web + open browser)
5. **Secrets never in SQLite plaintext** — OS keyring when available; gitignored local secret file fallback with explicit warning

Non-secret preferences live in `runtime/user_settings.json` (overlay on env defaults).

Out of Sprint 1: Generation Review redesign, Project zip export, CSP round-trip watcher,
Eagle sync, real Publish, Tauri packaging.

## Consequences

- Creators can configure and open a Project without editing `.env`.
- Env vars remain valid for CI / E2E (e2e/live-test still force Fake/Comfy via process env).
- Later sprints build Review / Backup / Eagle / Publish on this shell.
