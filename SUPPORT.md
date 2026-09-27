# Support

## Where to get help

We want you to succeed with AARK Kernel. Start with the documentation — most
questions are answered there.

| I want to… | Go to |
|---|---|
| Install and run the platform | [`docs/INSTALLATION.md`](docs/INSTALLATION.md) |
| Learn to use the dashboard, step by step | [`docs/USER_GUIDE_FA.md`](docs/USER_GUIDE_FA.md) · [`docs/USER_GUIDE_EN.md`](docs/USER_GUIDE_EN.md) |
| Call the API | [`docs/API.md`](docs/API.md) |
| Understand the design | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Know what is coming next | [`ROADMAP.md`](ROADMAP.md) |
| See what changed | [`CHANGELOG.md`](CHANGELOG.md) |

## Reporting a problem

**For bugs and feature requests**, open an issue and use the template. It asks
for exactly what we need to reproduce the problem: steps, expected behaviour,
actual behaviour, logs, and your environment.

[Open an issue](https://github.com/ansariaiadmin/aark-kernel/issues/new/choose)

**For security vulnerabilities, do not open an issue.** Report them privately —
see [`SECURITY.md`](SECURITY.md). A public report exposes every deployment before
a fix exists.

## Contact the maintainer

For questions that are not bugs — installation help, deployment advice, using
AARK Kernel in your own workflow, or collaboration — reach out directly:

| Channel | Handle |
|---|---|
| Telegram | [@ansariaiadmin](https://t.me/ansariaiadmin) |
| GitHub issues | [Open an issue](https://github.com/ansariaiadmin/aark-kernel/issues/new/choose) |
| Email | `hello@ansariai.ir` |

Please keep security vulnerabilities out of Telegram — report those privately as
described in [`SECURITY.md`](SECURITY.md).

## Response expectations

This is a community-maintained open-source project. There is no paid support
tier and no guaranteed response time, but in practice:

| Channel | Expected response |
|---|---|
| Security reports | Acknowledged within 24 hours |
| Telegram (general questions) | Usually within a day or two |
| Bug reports with a reproduction | Usually within a few days |
| Feature requests | Reviewed during roadmap planning |
| Pull requests | Reviewed within a week |

## Before you ask

Please do these first — they resolve the majority of reports:

```bash
./status.sh          # is every service healthy?
./logs.sh backend    # what does the backend say?
./smoke-test.sh      # does the full chain work?
```

Also check whether your question is already answered in
[`ROADMAP.md`](ROADMAP.md). If a behaviour you consider a bug is listed there as
planned work, it is not a bug — it is a gap we have documented and are tracking.

## Contributing a fix

If you would rather fix it than report it, we would be glad of the help.
[`CONTRIBUTING.md`](CONTRIBUTING.md) explains the quality gates your change needs
to pass.
