# Contributing to VT Platform («Взлёт талантов»)

Thank you for contributing. This guide defines how we collaborate on the repository: our branching model, naming and commit conventions, pull-request rules, and the day-to-day coding workflow. These rules keep `main` releasable at all times and our history clean, reviewable, and traceable.

> Full engineering standards are defined in [ARCH-001 §26 Coding Standards](docs/architecture/ARCH-001-vt-platform-architecture.md#26-coding-standards), [§27 Git Strategy](docs/architecture/ARCH-001-vt-platform-architecture.md#27-git-strategy), and [§28 Testing Strategy](docs/architecture/ARCH-001-vt-platform-architecture.md#28-testing-strategy). This document is the practical, day-to-day companion to them.

---

## 1. Git Flow

We use **trunk-based development with short-lived branches**.

- **`main`** is the single long-lived branch and is **always releasable**.
  - While the repository has a **single author**, changes land on `main` directly. There is no
    second person to review a pull request, and a PR one opens and merges oneself is paperwork
    rather than a control. What actually keeps `main` releasable is §6: CI gates every push, and
    nothing reaches production without passing the stand and a deliberate release.
  - **The moment a second author commits, §4 applies** — `main` is protected, direct pushes are
    off, and every change arrives via a reviewed pull request. Turn on branch protection with
    that person's first commit, not later.
- **Feature branches** are short-lived (ideally merged within ~2 days), branched from `main`, and deleted after merge.
- **`redesign`** is the one deliberate exception to that rule: the front-end redesign is drawn in
  Figma screen by screen and cannot land in pieces, because a half-restyled личный кабинет is
  worse than either version of it. The branch therefore lives for weeks and merges once, when the
  ЛК is whole.
  - **Merge `main` into it every day or two.** A branch that diverges for a month stops being a
    branch and becomes a fork; the cost of a long branch is paid either in small daily merges or
    in one unmanageable one at the end.
  - **Keep it to the front end.** It shares the stand's database with `main` (§6), and migrations
    do not roll back when the stand changes hands. A model change on this branch breaks the stand
    for hotfix testing — at which point the branch needs a stand of its own, not a workaround.
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
| `redesign` | The long-lived front-end redesign branch (§1) — no prefix, there is only ever one |

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
- **task reference:** work that comes from a YouGile card carries a `Refs:` footer naming it.
  This is not bookkeeping for its own sake — the deploy pipeline reads that trailer and puts the
  list of cards into the Telegram message announcing the stand, so the tester learns which cards
  to pull into the approval column without anyone writing it out by hand. A commit with no card
  behind it (a typo fix, a dependency bump) simply has no footer.

```
fix(judging): prevent scoring before round opens

Refs: VT-142
```

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

## 6. From a push to production

Two hosts, three decisions, and only one of them is automatic.

```
push в main
    │
    ▼
CI (ci.yml) ── красный ──▶ стоп, дальше ничего не происходит
    │ зелёный
    ▼
образы собираются и тегаются SHA коммита  ─┐
    │                                       │ один и тот же артефакт
    ▼                                       │ едет и на стенд, и в прод
STAGING обновляется автоматически          ─┘
test.vzlettalantov.by
    │
    ▼  бот пишет в TG, что приехало (список карточек из Refs:)
Настя тестирует по задачам и согласовывает их в YouGile
    │
    ▼  когда набор согласован — решение о моменте выкатки
Actions → Release → Run workflow   ← вручную, всегда
    │
    ▼
PRODUCTION
```

**Staging is not a decision.** It refreshes itself on every green `main` and has no approval gate.
A gate there would only mean the stand is stale exactly when somebody is waiting to test on it.

**The QA verdict lives in YouGile, not in GitHub.** It is per *task*, which is the granularity
testing actually happens at; a button in Actions would be per *commit*, and would have to stand in
for a set of cards that are rarely all finished at once. One verdict in one place.

**The release is a separate decision, and it is about the moment.** "Tested" and "ship it now" are
not the same judgement: a demo may be running, a feature may be embargoed until a date, half a
card may be on the stand. So production never deploys on its own — somebody starts `Release`, and
not starting it is how "not today" is expressed.

**Production can only receive a SHA that has been on the stand.** `release.yml` builds nothing; it
promotes images that `staging.yml` already published, and refuses outright if they are missing.
That is what makes what ships byte-for-byte what was tested, rather than a rebuild that merely
came from the same source.

**Rolling back is the same button with an older SHA.** There is no separate emergency path to
remember, which means the rollback path is the one that has already run hundreds of times.

### One stand, two branches

There is a single stand and the redesign occupies it for weeks, so the stand changes hands. What
makes that safe is that **building images and occupying the stand are separate steps**: every green
push on either branch produces images tagged with its SHA, whoever owns the stand. `Release`
promotes images, so a production fix is always releasable — even mid-redesign, when the stand is
showing something else entirely.

Ownership is one repository variable, `STAGING_TRACK`, and it defaults to `main` when unset — so
until somebody changes it, nothing about the pipeline behaves differently from before.

**Передать стенд редизайну:** Settings → Secrets and variables → Actions → Variables →
`STAGING_TRACK` = `redesign`. Вернуть — то же поле, значение `main`. (С установленным `gh`:
`gh variable set STAGING_TRACK -b redesign`.)

The owning branch rolls out automatically on every green push. The other branch builds images, says
so in Telegram, and leaves the stand alone.

**Пожар на проде, пока стенд за редизайном.** Стенд трогать не нужно:

1. Фикс коммитом в `main`, `git push`.
2. Дождаться зелёного CI — в Telegram придёт «образы собраны, стенд за веткой redesign».
3. Actions → **Release** → Run workflow → `sha` из этого сообщения.

Хочешь сперва проверить фикс на стенде — Actions → **Staging** → Run workflow, выбрать ветку `main`
в дропдауне; после релиза запустить то же самое с веткой `redesign`, чтобы вернуть картинку Насте.
Dispatch показывает ветку на стенде разово и **не** меняет владельца: следующий зелёный пуш в
ветку-владельца заберёт стенд назад сам.

Two tags track where things are, and both are moved by the pipeline:

```bash
git log staging..main       # написано, но ещё не на стенде
git log production..staging # на стенде, но ещё не выкачено
```

Host setup, the environments and their variables: [OPS-001](docs/devops/OPS-001-deploy-runbook.md)
— §5 for the GitHub side, §10 for the staging machine.

---

By contributing, you agree that your contributions follow these conventions and the standards referenced in the architecture documentation.
