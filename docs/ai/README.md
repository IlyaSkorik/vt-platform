# AI Documentation

## Purpose

Govern how AI is used *within the product* and *within the engineering workflow*: where AI features are applied, the guardrails around them, and a versioned library of reusable prompts.

## Scope

- **In scope:** AI use-case catalogue (e.g. originality/plagiarism checks, content moderation, jury-assist suggestions), governance & safety guardrails (especially for minors' data), human-in-the-loop rules, evaluation criteria, and the reusable **prompt library** in [`prompts/`](prompts/).
- **Out of scope:** general architecture (see [../architecture](../architecture/README.md)) and non-AI features.

## Governance Principles

- **Advisory, never decisive:** AI assists humans (e.g. jury) but never makes final scoring or eligibility decisions.
- **Privacy first:** minors' personal data is never sent to systems that violate the platform's privacy posture (see [ARCH-001 §21.6](../architecture/ARCH-001-vt-platform-architecture.md#21-security)).
- **Traceable & evaluable:** AI-assisted outputs are logged and measurable against defined evaluation criteria.

## Prefix

Documents in this domain use the `AI-` prefix (e.g. `AI-001-usage-policy.md`).

## Prompts Library

`prompts/` holds reusable, versioned prompts. Each prompt is a Markdown file with front-matter (purpose, model, inputs, version, owner) so prompts are reviewable and diff-able like any other artifact.

## Documents

| ID | Title | Status |
|----|-------|--------|
| — | _No documents yet._ | — |

## Future Documents

- `AI-001` — AI usage policy & governance.
- `AI-002` — AI use-case catalogue (moderation, originality, jury-assist).
- `AI-003` — Prompt authoring & versioning guidelines.
- `AI-004` — Evaluation & quality criteria for AI features.
- `prompts/` — Individual versioned prompt files.
