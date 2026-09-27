#!/usr/bin/env python3
"""Regenerate docs/API.md from the live OpenAPI schema.

`docs/API.md` used to be handwritten and had drifted so far that it documented
`POST /api/auth/login` (missing the `/v1` prefix) and
`POST /api/notifications/send` (an endpoint that has never existed), while
omitting all 34 real routes.

Generating it removes the possibility of drift. CI verifies freshness via
`tests/test_release_consistency.py::test_api_docs_are_up_to_date`.

Usage:
    cd backend && python scripts/generate_api_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
OUT = REPO_ROOT / "docs" / "API.md"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

HEADER = """# API Reference — aark-kernel

> **این فایل تولیدشده است — دستی ویرایشش نکنید.**
>
> Generated from the live OpenAPI schema by
> `backend/scripts/generate_api_docs.py`. Editing it by hand is how the previous
> copy drifted into documenting endpoints that do not exist.
>
> Regenerate:
> ```bash
> cd backend && python scripts/generate_api_docs.py
> ```
> CI fails if this file is out of date.

## احراز هویت

روت‌ها سه وضعیت دسترسی دارند (تعریف در `backend/app/api/v1/__init__.py`):

| دسته | پیشوند/مسیرها | احراز هویت |
|---|---|---|
| **Public** | `health/*`, `metrics`, `auth/login`, `nobitex/status`, `agents` | بدون توکن |
| **Protected** | `ai/*`, `trading/*`, `risk/*`, `auth/me`, `auth/users*` | `Authorization: Bearer <JWT>` |
| **Realtime** | `ws/ws` | کوئری `?token=<JWT>` در handshake |

### گرفتن توکن

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \\
  -H 'Content-Type: application/x-www-form-urlencoded' \\
  -d 'username=admin@aark-kernel.dev&password=<ADMIN_PASSWORD>' \\
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
```

توکن ۳۰ دقیقه اعتبار دارد (`ACCESS_TOKEN_TTL_MINUTES` در `app/core/auth.py`).

حساب ادمین هنگام اولین راه‌اندازی از `ADMIN_EMAIL` / `ADMIN_PASSWORD` در `.env`
ساخته می‌شود (`app/db/init_db.py::bootstrap_admin`).

### WebSocket

```
ws://<host>/api/v1/ws/ws?token=<JWT>
```

پیام‌های کلاینت:

```json
{"type": "subscribe",   "topic": "market.BTCUSDT"}
{"type": "unsubscribe", "topic": "market.BTCUSDT"}
{"type": "ping"}
{"type": "get_status"}
```

پیام‌های سرور: `connected`, `subscribed`, `unsubscribed`, `pong`, `status`,
`heartbeat`, `market_update`, `order_update`, `position_update`, `risk_alert`,
`portfolio_update`, `agent_message`, `notification`.

توکن نامعتبر یا منقضی → بسته‌شدن با کد `1008`.

---

"""


def _render(schema: dict) -> str:
    from app.core.config import get_settings

    settings = get_settings()
    info = schema.get("info", {})
    paths = schema.get("paths", {})
    components = schema.get("components", {}).get("schemas", {})

    out = [HEADER]
    out.append(
        f"**App:** {info.get('title', settings.APP_NAME)}  \n"
        f"**Version:** {info.get('version', settings.APP_VERSION)}  \n"
        f"**Routes:** {len(paths)} paths  \n"
        f"**Prefix:** `{settings.API_V1_PREFIX}`\n\n---\n"
    )

    # Group by tag so the doc mirrors the router split.
    by_tag: dict[str, list[tuple[str, str, dict]]] = {}
    for path, ops in sorted(paths.items()):
        for method, op in sorted(ops.items()):
            if method in ("parameters", "summary", "description"):
                continue
            tag = (op.get("tags") or ["Untagged"])[0]
            by_tag.setdefault(tag, []).append((method.upper(), path, op))

    out.append("## فهرست\n")
    for tag in sorted(by_tag):
        anchor = tag.lower().replace(" ", "-").replace("&", "").replace("/", "")
        out.append(f"- [{tag}](#{anchor}) — {len(by_tag[tag])} operation(s)")
    out.append("\n---\n")

    for tag in sorted(by_tag):
        out.append(f"\n## {tag}\n")
        for method, path, op in by_tag[tag]:
            summary = op.get("summary", "")
            out.append(f"### `{method}` `{path}`\n")
            if summary:
                out.append(f"{summary}\n")
            desc = op.get("description")
            if desc and desc.strip() != summary.strip():
                first = desc.strip().split("\n\n")[0]
                out.append(f"\n{first}\n")

            params = op.get("parameters", [])
            if params:
                out.append("\n**Parameters**\n")
                out.append("| Name | In | Type | Required |\n|---|---|---|---|")
                for prm in params:
                    sch = prm.get("schema", {})
                    ptype = sch.get("type") or _ref_name(sch) or "—"
                    required = "✅" if prm.get("required") else "—"
                    out.append(f"| `{prm.get('name')}` | {prm.get('in')} | {ptype} | {required} |")
                out.append("")

            body = op.get("requestBody")
            if body:
                content = body.get("content", {})
                for ctype, spec in content.items():
                    sch = spec.get("schema", {})
                    name = _ref_name(sch)
                    out.append(f"\n**Request body** — `{ctype}`" + (f" → `{name}`" if name else ""))
                    if name and name in components:
                        out.append(_render_schema_table(components[name], components))

            responses = op.get("responses", {})
            codes = ", ".join(f"`{c}`" for c in sorted(responses))
            out.append(f"\n**Responses:** {codes}\n")

    out.append("\n---\n\n## Schemas\n")
    for name in sorted(components):
        out.append(f"\n### `{name}`\n")
        out.append(_render_schema_table(components[name], components))

    out.append(
        "\n---\n\n"
        "## نکات قراردادها\n\n"
        "- در FastAPI پارامترهای **scalar** یک endpoint `POST` به‌صورت پیش‌فرض "
        "*query* هستند و پارامترهای غیرscalar (dict/model) *body*. "
        "ترکیب این دو در یک endpoint باعث قرارداد گیج‌کننده می‌شود — "
        "`/risk/validate` قبلاً به همین دلیل همیشه `422` می‌داد. "
        "همهٔ این endpointها حالا مدل درخواست صریح دارند.\n"
        "- `/docs` (Swagger UI) فقط وقتی `DEBUG=true` باشد فعال است.\n"
        "- پاسخ خطاها شامل `correlation_id` است که در هدر `X-Correlation-ID` هم می‌آید.\n"
    )
    return "\n".join(out)


def _ref_name(schema: dict) -> str | None:
    ref = schema.get("$ref")
    if ref:
        return ref.rsplit("/", 1)[-1]
    return None


def _render_schema_table(schema: dict, components: dict) -> str:
    props = schema.get("properties")
    if not props:
        return "\n_(free-form object)_\n"
    required = set(schema.get("required", []))
    rows = ["", "| Field | Type | Required |", "|---|---|---|"]
    for fname, fspec in props.items():
        ftype = fspec.get("type") or _ref_name(fspec) or "—"
        if ftype == "array":
            items = fspec.get("items", {})
            ftype = f"array<{items.get('type') or _ref_name(items) or 'any'}>"
        rows.append(f"| `{fname}` | {ftype} | {'✅' if fname in required else '—'} |")
    rows.append("")
    return "\n".join(rows)


def main() -> int:
    from app.main import app

    schema = app.openapi()
    text = _render(schema)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(schema['paths'])} paths, {len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
