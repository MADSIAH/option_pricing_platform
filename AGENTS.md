# AGENTS.md

This file documents how AI tools are used in this repository and how human contributors validate AI-assisted work.

## Purpose

- Describe the role of AI assistants in development.
- Define guardrails for financial correctness and code quality.
- Keep a clear, auditable workflow for AI-supported commits and pull requests.

## AI Scope In This Project

AI tools may assist with:

- code scaffolding and refactoring
- test generation and edge-case discovery
- documentation drafting and editing
- debugging support and review suggestions

AI tools must not be treated as authoritative sources for quantitative finance assumptions.

## Human Ownership And Review

- Final responsibility always remains with human contributors.
- Every AI-generated code change must be reviewed before merge.
- Numerical formulas, model assumptions, and units must be validated against trusted references.
- Any behavioral change in pricing or Greeks must be covered by tests.

## Workflow For AI-Supported Changes

1. Create or update code with AI assistance in a branch.
2. Run local tests (`python -m pytest -q`) before opening a PR.
3. In the PR description, label AI-assisted sections and summarize what was validated manually.
4. Merge only after human review and green checks.

## Commit And PR Guidelines

- Use clear commit messages that describe the functional change.
- Prefer small, focused PRs (one concern per PR).
- Avoid committing secrets, credentials, or private data.
- Keep notebook outputs and generated artifacts under control.

## Compliance Note

This repository follows course expectations for AI-supported collaboration by documenting AI usage and enforcing human validation before merge.
