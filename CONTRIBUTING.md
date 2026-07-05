# Contributing to VT Platform («Взлёт талантов»)

Thank you for contributing. This guide defines how we collaborate on the repository: our branching model, naming and commit conventions, pull-request rules, and the day-to-day coding workflow. These rules keep `main` releasable at all times and our history clean, reviewable, and traceable.

> Full engineering standards are defined in [ARCH-001 §26 Coding Standards](docs/architecture/ARCH-001-vt-platform-architecture.md#26-coding-standards), [§27 Git Strategy](docs/architecture/ARCH-001-vt-platform-architecture.md#27-git-strategy), and [§28 Testing Strategy](docs/architecture/ARCH-001-vt-platform-architecture.md#28-testing-strategy). This document is the practical, day-to-day companion to them.

---

## 1. Git Flow

We use **trunk-based development with short-lived branches**.

- **`main`** is the single long-lived branch and is **always releasable**. It is protected: no direct pushes; all changes arrive via reviewed pull requests.
- **Feature branches** are short-lived (ideally merged within ~2 days), branched from `main`, and deleted after merge.
- **`release/*`** branches are used only when a versioned release needs hardening/stabilization before tagging.
- **`hotfix/*`** branches address urgent production defects, branched from `main` (or the release tag) and merged back immediately.

```
main ─────●───────────●───────────●────────▶  (always releasable)
           \         / \         /
    feat/... ●──●──●    fix/... ●──●
```

Keep branches small and focused. Rebase onto the latest `main` before opening or updating a PR; prefer rebase over merge commits to preserve a linear history.

## 2. Branch Naming

```
<type>/<short-kebab-case-description>
```

| Type | Use for |
|------|---------|
| `feat/` | New feature or capability |
| `fix/` | Bug fix |
| `docs/` | Documentation only |
| `chore/` | Tooling, config, dependencies, housekeeping |
| `refactor/` | Code change that neither fixes a bug nor adds a feature |
| `test/` | Adding or improving tests |
| `perf/` | Performance improvement |
| `ci/` | CI/CD pipeline changes |
| `release/` | Release stabilization branch |
| `hotfix/` | Urgent production fix |

Optionally prefix with an issue key: `feat/VT-142-participant-registration`.

**Examples**
- `feat/submission-media-upload`
- `fix/jury-score-rounding`
- `docs/adr-media-pipeline`

## 3. Commit Message Convention

We follow **[Conventional Commits](https://www.conventionalcommits.org/)**:

```
<type>(<scope>): <subject>

<body — optional: what & why, not how>

<footer — optional: BREAKING CHANGE:, Refs: VT-123>
```

- **type:** `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `ci`, `build`, `style`, `revert`.
- **scope:** the affected area, e.g. `judging`, `api`, `frontend`, `repo`.
- **subject:** imperative mood, lowercase, no trailing period, ≤ ~72 chars ("add", not "added").
- **breaking changes:** add a `!` after the type/scope (`feat(api)!: …`) **and** a `BREAKING CHANGE:` footer.

**Examples**
```
feat(submissions): accept pre-signed S3 uploads
fix(judging): prevent scoring before round opens
docs(repo): bootstrap enterprise documentation structure
refactor(identity)!: replace session auth with JWT

BREAKING CHANGE: session cookies are no longer accepted.
```

Conventional Commits drive our changelog generation and SemVer versioning, so accuracy matters.

## 4. Pull Request Rules

A PR may be merged only when **all** of the following hold:

1. **Green CI** — lint, type-check, tests, build, and security scans all pass.
2. **Reviewed** — at least **one** approving review (**two** for security-, auth-, privacy-, or data-migration-sensitive changes).
3. **Small & focused** — one logical change per PR; decompose large work.
4. **Described** — the PR description states *what* and *why*, links the issue, and lists notable decisions. Architecture-affecting PRs reference the relevant **ADR**.
5. **No breaking API changes** without a version bump and the appropriate label (see [API docs](docs/api/README.md)).
6. **Definition of Done met** — tests, docs, and observability (logs/metrics) updated for new behavior.
7. **Merge strategy** — **squash merge** into `main` with a Conventional-Commit title; the feature branch is deleted after merge.

Draft PRs are welcome for early feedback. Convert to "Ready for review" only when the checklist above is satisfiable.

## 5. Coding Workflow

1. **Sync & branch** — update `main`, create a `<type>/<slug>` branch.
2. **Design first** — for non-trivial work, align on approach; record architectural decisions as an **ADR** ([how](docs/architecture/ADR/README.md)).
3. **Code to standards** — follow the language standards in [ARCH-001 §26](docs/architecture/ARCH-001-vt-platform-architecture.md#26-coding-standards). Keep the domain framework-free; no business logic in views/serializers.
4. **Test** — add/extend unit, integration, and (where relevant) E2E tests. Meet coverage gates.
5. **Run checks locally** — format, lint, type-check, and test before pushing (the same gates CI enforces).
6. **Commit** — small, meaningful, Conventional-Commit messages.
7. **Open a PR** — fill the description, link the issue, request review.
8. **Address review** — respond to every comment; push follow-up commits (squashed on merge).
9. **Merge** — once green and approved, squash-merge and delete the branch.

---

By contributing, you agree that your contributions follow these conventions and the standards referenced in the architecture documentation.
