# 0011. Structurizr DSL is the source of truth for architecture diagrams

- Status: accepted
- Date: 2026-09-07
- Design reference: docs/DESIGN.md, decision D11

## Context

Hand-drawn diagrams rot the day after they are made. The owner asked for diagrams maintained the same way as infrastructure.

## Decision

docs/c4/workspace.dsl holds one C4 model with context, container, component and deployment views. CI exports it to Mermaid and fails a PR whose generated diagrams are stale. From milestone M8, a drift check compares container identifiers in the model against c4_container tags on Terraform resources and labels on Helm releases.

## Consequences

Diagrams exist before the first resource and cannot silently disagree with it afterwards; Docker is required to regenerate locally.
