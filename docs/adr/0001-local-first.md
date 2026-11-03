# ADR-0001 — Local-first, cloud-optional architecture

- Status: Accepted
- Date: 2026-11-03

## Context
A portfolio project should be demonstrable without paid cloud resources.

## Decision
Build a reproducible local domain/source before adding an optional BigQuery deployment. Keep cloud provisioning opt-in and use deterministic synthetic business data.

## Consequences
- Lower barrier to evaluation.
- CI can validate business rules without cloud credentials.
- Cloud-specific cost and security will be evaluated separately.
- A local simulation alone cannot prove production scalability.
