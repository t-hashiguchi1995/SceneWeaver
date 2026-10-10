# ADR 0002 — Shot/GenerationAttempt persistence deferred to in-memory for MVP slice

## Status

Superseded by ADR 0004

## Context

M4 originally kept ShotPipeline state in-process to prove the vertical slice quickly.

## Decision (original)

MVP kept ShotPipeline state in-process (singleton on Container).

## Consequences

Superseded: ShotSpec / RenderPlan / GenerationAttempt are now SQL-backed
(see ADR 0004).
