# User Guide — AARK Kernel

**Version:** 3.3.0
**Audience:** anyone — no technical background required
**Time to first run:** under 5 minutes

---

## Contents

1. [What this does](#what-this-does)
2. [Prerequisites](#prerequisites)
3. [Step-by-step installation](#step-by-step-installation)
4. [Your first sign-in](#your-first-sign-in)
5. [A tour of the dashboard](#a-tour-of-the-dashboard)
6. [Everyday tasks](#everyday-tasks)
7. [Keeping it safe](#keeping-it-safe)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## What this does?

AARK Kernel is a **trading and risk-management dashboard**. It does three things well:

### 1. Shows the market, live

Prices refresh every few seconds and render on a live chart. The order book
updates in real time.

### 2. Computes risk — before your money is exposed

This is the core. The risk engine answers:

| Your question | What the platform returns |
|---|---|
| "If the market drops 5% tomorrow, how much do I lose?" | An exact figure |
| "What is the worst plausible case?" | 6 stress scenarios: severe crash, crypto winter, flash crash, and more |
| "How concentrated is my portfolio?" | Herfindahl-Hirschman Index (HHI) |
| "How many units should I buy?" | A position size derived from volatility |

### 3. Keeps your exchange key in a vault

Your Nobitex API key is stored in an isolated vault: a `0700` directory
containing a `0600` file, written atomically. The key is **never stored in the
database**, so a database leak does not expose it.

---

## Prerequisites

| Requirement | Where to get it | Required? |
|---|---|---|
| Docker Desktop | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) | ✅ Yes |
| Git | [git-scm.com/downloads](https://git-scm.com/downloads) | ✅ Yes |
| 4 GB free RAM | — | ✅ Yes |
| Ports 3000 and 8000 free | — | ✅ Yes |
| Ollama + `qwen2.5:7b` model | [ollama.com](https://ollama.com/) | ⬜ Optional |

> **What is Ollama and do I need it?** Ollama runs a language model locally on
> your machine — free, and no data leaves your computer. Without it, everything
> works **except** conversation with the AI agent.

---

## Step-by-step installation

### Step 1 — Get the code

Open a terminal (Windows: PowerShell or Command Prompt):

```bash
git clone https://github.com/ansariaiadmin/aark-kernel.git
cd aark-kernel
```

### Step 2 — Run the installer

```bash
chmod +x install.sh
./install.sh
```

**What it asks you:**

```
📧 Admin email:         admin@aark-kernel.dev
🔑 Admin password:      **************     (at least 12 characters)
```

**What it does for you:**

1. Verifies Docker is available
2. Generates `.env` with strong random secrets
3. Starts PostgreSQL and Redis
4. Builds and starts the backend and the dashboard
5. **Creates your admin account in the database** so you can sign in

⏱ Usually takes 2–4 minutes depending on your connection.

### Step 3 — Sign in

Open your browser and go to:

```
http://localhost:3000
```

Use the email and password from Step 2.

> **If you see a blank page:** wait a few seconds and refresh. The dashboard is
> preparing itself on first load.

---

## A tour of the dashboard

After signing in you will see:

| Area | What you see | What you can do |
|---|---|---|
| **Top bar** | Your name, your role, a sign-out button | Sign out |
| **Summary cards** | Total portfolio value, daily P&L, open positions | — |
| **Price chart** | A live price line | Change the time range |
| **Tabs** | Portfolio · Orders · Risk · Agent | Move between sections |
| **Order book** | Best bid and ask prices | Watch it live |
| **Kill switch** | A red "Kill Switch" button | Halt all activity |

### The Risk tab — the important one

Here you can:

- Select the **VaR method**: historical, parametric, or Monte Carlo
- Enter the **portfolio value**
- Read the result: "with 95% confidence, your maximum loss is X"

> **VaR in plain language:** VaR means "the most you are likely to lose with
> 95% probability". If your VaR is 100,000, then only in 5% of cases will your
> loss exceed 100,000.

### The Kill Switch

The red button in the top bar. When pressed:

1. All pending orders are cancelled
2. No new orders are accepted
3. The state is recorded on screen and in the logs

---

## Everyday tasks

| I want to… | Command |
|---|---|
| Start the platform | `./start.sh` |
| Stop the platform | `./stop.sh` |
| Check what is running | `./status.sh` |
| Read backend logs | `./logs.sh backend` |
| Back up my configuration | `./backup.sh` |
| Update to the latest version | `./update.sh` |
| Verify everything is healthy | `./smoke-test.sh` |

> On Windows, the same commands use the `.bat` extension: `start.bat`,
> `status.bat`, and so on.

---

## Keeping it safe

### Do these

| # | Action | Why |
|---|---|---|
| 1 | Use a strong admin password (12+ characters, letters and digits) | Prevents guessing |
| 2 | Keep `.env` private: `chmod 600 .env` | All your secrets live there |
| 3 | Never commit `.env` to git | Already in `.gitignore` |
| 4 | Use encrypted backups (`./backup.sh`) | In case your disk fails |

### Never do these

- ❌ Paste your exchange API key into a public channel
- ❌ Send passwords in screenshots
- ❌ Expose the backend directly to the internet without an authenticating reverse proxy

---

## Troubleshooting

### "The page does not open"

```bash
./status.sh          # which service is down?
./logs.sh            # read the error
```

Most common cause: Docker Desktop is not running. Start it and run
`./start.sh` again.

### "I cannot sign in"

**Cause 1:** wrong password. Passwords are case-sensitive.

**Cause 2:** the admin account was never created. Check:

```bash
docker compose logs backend | grep -i "bootstrap"
```

You should see something like `Bootstrap admin created: admin@...`. If not, add
these two lines to `.env` and run `./update.sh`:

```
ADMIN_EMAIL=admin@aark-kernel.dev
ADMIN_PASSWORD=<a-strong-12-char-password>
```

### "Port already in use"

```bash
./stop.sh
# Windows: netstat -ano | findstr :3000
# Linux/macOS: lsof -i :3000
./start.sh
```

### "401 Unauthorized"

Your token expired (30 minutes). Sign in again. This is deliberate security
behaviour.

### "500 error on the Risk page"

Read the backend log first: `./logs.sh backend`. If the error mentions Ollama,
the language model is unavailable — the rest of the dashboard still works.

---

## FAQ

**Does this cost real money?**
No. In this version trading runs in **paper-trading mode**: orders are simulated
and no real funds move.

**Where is my data stored?**
On your own machine. PostgreSQL and the key vault are both local. No data is
sent to an external server.

**Can I use it on mobile?**
Yes. The app is a PWA: in a mobile browser choose "Add to Home Screen" and it
installs like a native app.

**Can several people use it at once?**
Yes. Roles are **Admin** (full control), **Trader** (trade), and **Viewer**
(read-only). An Admin creates users via `POST /api/v1/auth/register`.

**How do I enter my Nobitex API key?**
From the settings tab, call the key endpoint. The key is written to the vault
(`~/.aark`) with `0600` permissions.

> ⚠️ **Security note:** the key-storage endpoint in v3.3.0 still does not require
> a token. Until this is fixed in v3.4.0, run the backend only on the local
> network (`127.0.0.1`) or behind an authenticating reverse proxy.

---

<div align="center">

**Need technical detail?** [`docs/INSTALLATION.md`](INSTALLATION.md) ·
[`README.md`](../README.md) · [Report an issue](https://github.com/ansariaiadmin/aark-kernel/issues/new)

</div>
