# ADR 0009 — Japanese UI / Localization (v0.2 Sprint 2)

## Status

Accepted

## Context

Creators in the primary market read Japanese. Hardcoding Japanese strings blocks English fallback
and mixes API enums into the UI.

## Decision

- Use `i18next` + `react-i18next` with namespaces under `apps/web/src/i18n/locales/{ja,en}/`
- **Default locale: `ja`**, fallback: `en`
- Persist choice in `localStorage` (`sceneweaver.locale`); Settings exposes the switcher
- Keep API / Domain enums in English (`running`, `adopted`, `COMFY_UNREACHABLE`, …)
- Map status and error codes to localized copy only in the frontend
- Prefer `data-testid` for Playwright actions; assert Japanese visible copy where validating UX

## Consequences

- UI strings live in JSON, not inline in components
- E2E updated for Japanese status labels
- Domain names (`Beat`, `OutfitState`) may differ from UI labels (`展開`, `コーディネート`)
