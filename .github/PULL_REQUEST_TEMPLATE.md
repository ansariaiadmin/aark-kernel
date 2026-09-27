<!--
Thank you for contributing. Please fill in every section — a pull request with
an empty description will not be reviewed.
-->

## Problem

<!-- What is broken or missing? Link the issue this closes, if any. -->

Closes #

## Change

<!-- What you did, and why this approach rather than another one. -->

## Verification

<!-- Paste the real output. Reviewers will re-run these. -->

```bash
# Backend
cd backend && ruff check . && pytest tests/ -q

# Frontend
cd frontend && npm run verify

# Compose
docker compose config -q
```

**Result:**

```
ruff:
pytest:
eslint / tsc / build:
compose config:
```

## Risk and rollback

<!-- What could this break? How would you undo it? -->

## Documentation

- [ ] `CHANGELOG.md` updated for anything user-visible
- [ ] `docs/API.md` regenerated if an endpoint changed (`cd backend && python scripts/generate_api_docs.py`)
- [ ] No claim added that is not backed by a test or a runnable command
- [ ] No unrelated changes bundled into this pull request

## Checklist

- [ ] Tests added or updated — a bug fix includes a test that failed before the fix
- [ ] No new dependency without prior discussion
- [ ] No secrets, tokens, or credentials in the diff
- [ ] I have not pushed directly to `main`
