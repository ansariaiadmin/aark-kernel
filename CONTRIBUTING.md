# Contributing to AARK Kernel

**Version:** 3.3.0

Thank you for considering a contribution. This guide is written so that a
first-time contributor — technical or not — can make a useful change on the
first day.

---

## Contents

1. [Ways to contribute](#ways-to-contribute)
2. [Before you write code](#before-you-write-code)
3. [Setting up](#setting-up)
4. [Making a change](#making-a-change)
5. [Quality gates](#quality-gates)
6. [Commit messages](#commit-messages)
7. [Pull requests](#pull-requests)
8. [Coding standards](#coding-standards)
9. [Documentation standards](#documentation-standards)
10. [Reporting bugs](#reporting-bugs)

---

## Ways to contribute

You do not have to write code to help.

| Contribution | How |
|---|---|
| Report a bug | [Open an issue](https://github.com/ansariaiadmin/aark-kernel/issues/new) |
| Improve documentation | Fix a typo, clarify a step, translate a guide |
| Add or fix a test | Especially valuable — see [Quality gates](#quality-gates) |
| Review a pull request | A second pair of eyes catches real bugs |
| Answer a question | Issues and discussions |

---

## Before you write code

1. **Search existing issues** — someone may already be working on it
2. **Check the roadmap** — [`ROADMAP.md`](ROADMAP.md) lists planned work with
   task IDs and acceptance criteria. Pick something from there and it will not
   conflict with other work
3. **Open an issue first** for anything larger than a small fix, so we can agree
   on the approach before you spend effort

---

## Setting up

```bash
git clone https://github.com/ansariaiadmin/aark-kernel.git
cd aark-kernel
chmod +x install.sh
./install.sh
```

For local development without containers:

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -q

# Frontend
cd ../frontend
npm ci
npm run verify
```

> **Keep the virtual environment outside the repository** so it is never
> committed accidentally.

---

## Making a change

```bash
git checkout -b feat/short-description      # or fix/…, docs/…, test/…
# … make your change …
pytest tests/ -q                            # backend must stay green
npm run verify                              # frontend must stay green
git add -p                                  # review what you stage
git commit -m "feat: short description"
git push origin feat/short-description
```

Then open a pull request.

> **Never push directly to `main`.** Every change goes through a pull request
> and the CI gate.

---

## Quality gates

A pull request is mergeable only when all of these pass. CI runs them again, so
there is no point opening one early.

| Gate | Command | Requirement |
|---|---|---|
| Backend lint | `cd backend && ruff check .` | zero errors |
| Backend tests | `cd backend && pytest tests/ -q` | 109 passed, zero failures |
| Frontend lint | `cd frontend && npx eslint .` | zero errors |
| Frontend types | `cd frontend && npx tsc --noEmit` | zero errors |
| Frontend build | `cd frontend && npx next build` | exits 0 |
| Compose config | `docker compose config -q` | exits 0 |
| Docs freshness | `cd backend && python scripts/generate_api_docs.py` | produces no diff |

### Tests

- Every new behaviour needs a test. Bug fixes especially: write the test that
  fails before the fix, then make it pass.
- Tests must not require external services. SQLite and `ASGITransport` are used
  deliberately — mocking at the HTTP boundary is what previously allowed a
  broken password hash and several unauthenticated routes to survive unnoticed.
- Run a single test while iterating: `pytest tests/test_risk_engine.py -q`

---

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/). CI does not
enforce it, but reviewers rely on it.

```
<type>(<scope>): <imperative summary, ≤72 chars>

<why the change was needed — the problem, not the diff>

<what was verified>
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`,
`chore`, `security`

**Example:**

```
fix(auth): replace passlib with direct bcrypt calls

passlib 1.7.4 probes bcrypt.__about__, which was removed in bcrypt 4.x, and
raises on passwords longer than 72 bytes. Every login failed.

Direct bcrypt calls preserve the $2b$ prefix; 39 wiring tests pass.
```

---

## Pull requests

Use the pull request template. It asks for the problem, the change, the
verification, and the risk.

**Review expectations:**

- At least one maintainer approval
- CI green
- Documentation updated if behaviour changed
- No unrelated changes bundled in

**If your PR is large**, split it. A 20-file pull request is hard to review and
will wait longer than three small ones.

---

## Coding standards

### Python

- Formatted and checked with `ruff` (line length 100)
- Type hints on all public functions
- No `print()` — use the structured logger
- Business logic lives in `services/` or `risk_engine/`, not in route handlers
- Route handlers marshal data and delegate; they do not compute

### TypeScript / React

- Strict mode, no `any`
- Components stay presentational; data access goes through `src/lib/api.ts`
- Browser code must never call the backend origin directly — use the same-origin
  `/api/v1/*` path so the Next rewrite handles it
- No new dependency without a discussion — the dependency surface is a security
  surface

### What we will ask you to change

- A route that computes risk maths inline instead of calling `risk_engine`
- A new hardcoded secret or URL
- A test that mocks HTTP instead of using `ASGITransport`
- A documentation claim that is not backed by a test or a runnable command

---

## Documentation standards

Documentation is a product surface, not an afterthought.

1. **Every claim is verifiable.** If you write "the platform does X", either a
   test proves it or a command demonstrates it.
2. **No aspirational language.** Do not document a feature that does not exist.
   If it is planned, it belongs in [`ROADMAP.md`](ROADMAP.md).
3. **Update `CHANGELOG.md`** for anything user-visible.
4. **Regenerate `docs/API.md`** if you touch an endpoint:
   `cd backend && python scripts/generate_api_docs.py`. A test fails if the
   committed copy is stale.
5. **Explain the *why*.** A reader who understands the reason will not undo your
   change in six months.

---

## Reporting bugs

A good report gets fixed. A vague one gets closed.

Please include:

1. What you did
2. What you expected
3. What actually happened
4. The exact error message or log excerpt
5. Your environment: OS, Docker version, browser
6. `./status.sh` output if the platform is running

Use the bug report template — it asks for exactly these.

---

## Code of conduct

Participation in this project is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md). Be decent to each other.

---

<div align="center">

[`README.md`](README.md) · [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) ·
[`ROADMAP.md`](ROADMAP.md) · [Open an issue](https://github.com/ansariaiadmin/aark-kernel/issues/new)

</div>
