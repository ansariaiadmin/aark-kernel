# API Reference — aark-kernel

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
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin@aark-kernel.dev&password=<ADMIN_PASSWORD>' \
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


**App:** AARK Kernel Ops  
**Version:** 3.3.0  
**Routes:** 39 paths  
**Prefix:** `/api/v1`

---

## فهرست

- [Advanced AI](#advanced-ai) — 8 operation(s)
- [Advanced Risk Management](#advanced-risk-management) — 7 operation(s)
- [Authentication & Authorization](#authentication--authorization) — 8 operation(s)
- [External Integrations](#external-integrations) — 1 operation(s)
- [Health & Monitoring](#health--monitoring) — 4 operation(s)
- [Multi-Agent Gateway](#multi-agent-gateway) — 3 operation(s)
- [Trading Engine](#trading-engine) — 9 operation(s)
- [Untagged](#untagged) — 4 operation(s)

---


## Advanced AI

### `POST` `/api/v1/ai/agent/chat`

Agent Chat


**Request body** — `application/json` → `ChatRequest`

| Field | Type | Required |
|---|---|---|
| `message` | string | ✅ |
| `model` | — | — |
| `use_tools` | boolean | — |
| `stream` | boolean | — |
| `system_prompt` | — | — |


**Responses:** `200`, `422`

### `POST` `/api/v1/ai/agent/evaluate/stream`

Evaluate Stream


**Request body** — `application/json` → `EvaluateStreamRequest`

| Field | Type | Required |
|---|---|---|
| `wallet_balance_irt` | number | ✅ |
| `market_context` | string | ✅ |


**Responses:** `200`, `422`

### `POST` `/api/v1/ai/agent/memory/clear`

Clear Memory


**Responses:** `200`

### `GET` `/api/v1/ai/agent/memory/summary`

Get Memory Summary


**Responses:** `200`

### `GET` `/api/v1/ai/models`

List Models


**Responses:** `200`

### `POST` `/api/v1/ai/models/register`

Register Model


**Request body** — `application/json` → `ModelRegisterRequest`

| Field | Type | Required |
|---|---|---|
| `name` | string | ✅ |
| `provider` | string | ✅ |
| `base_url` | string | ✅ |
| `api_key` | — | — |
| `max_tokens` | integer | — |
| `temperature` | number | — |
| `supports_tools` | boolean | — |
| `supports_streaming` | boolean | — |
| `priority` | integer | — |


**Responses:** `200`, `422`

### `GET` `/api/v1/ai/tools`

List Tools


**Responses:** `200`

### `POST` `/api/v1/ai/tools/execute`

Execute Tool


**Parameters**

| Name | In | Type | Required |
|---|---|---|---|
| `tool_name` | query | string | ✅ |


**Request body** — `application/json`

**Responses:** `200`, `422`


## Advanced Risk Management

### `GET` `/api/v1/risk/correlation`

Get Correlation Risk


Analyze correlation risk across positions.


**Parameters**

| Name | In | Type | Required |
|---|---|---|---|
| `symbols` | query | array | ✅ |
| `lookback_days` | query | integer | — |


**Responses:** `200`, `422`

### `POST` `/api/v1/risk/legacy/validate`

Legacy Validate Order


Backward compatible risk validation endpoint.


**Request body** — `application/json` → `LegacyValidateRequest`

| Field | Type | Required |
|---|---|---|
| `current_balance_irt` | number | ✅ |
| `requested_amount_irt` | number | ✅ |


**Responses:** `200`, `422`

### `POST` `/api/v1/risk/position-size`

Calculate Position Size


Calculate dynamic position size based on risk parameters.


**Request body** — `application/json` → `PositionSizeRequest`

| Field | Type | Required |
|---|---|---|
| `symbol` | string | ✅ |
| `signal_strength` | number | ✅ |
| `volatility` | number | ✅ |
| `portfolio_value` | number | ✅ |
| `current_positions` | object | — |
| `prices` | object | — |
| `max_risk_per_trade` | number | — |


**Responses:** `200`, `422`

### `POST` `/api/v1/risk/stress-test`

Run Stress Test


Run portfolio stress tests against the 6 built-in (or custom) scenarios.


**Request body** — `application/json` → `StressTestRequest`

| Field | Type | Required |
|---|---|---|
| `positions` | object | — |
| `prices` | object | — |
| `scenarios` | — | — |


**Responses:** `200`, `422`

### `GET` `/api/v1/risk/summary`

Get Risk Summary


Get current risk engine configuration and state.


**Responses:** `200`

### `POST` `/api/v1/risk/validate`

Validate Portfolio Risk


Comprehensive portfolio risk validation.


**Request body** — `application/json` → `RiskValidateRequest`

| Field | Type | Required |
|---|---|---|
| `positions` | object | — |
| `prices` | object | — |
| `daily_pnl` | number | — |
| `portfolio_value` | number | ✅ |
| `returns_history` | — | — |


**Responses:** `200`, `422`

### `GET` `/api/v1/risk/var`

Get Var


Calculate Value at Risk using specified method.


**Parameters**

| Name | In | Type | Required |
|---|---|---|---|
| `method` | query | string | — |
| `confidence` | query | number | — |
| `portfolio_value` | query | number | ✅ |


**Responses:** `200`, `422`


## Authentication & Authorization

### `POST` `/api/v1/auth/login`

Login


**Request body** — `application/x-www-form-urlencoded` → `Body_login_api_v1_auth_login_post`

| Field | Type | Required |
|---|---|---|
| `grant_type` | — | — |
| `username` | string | ✅ |
| `password` | string | ✅ |
| `scope` | string | — |
| `client_id` | — | — |
| `client_secret` | — | — |


**Responses:** `200`, `422`

### `GET` `/api/v1/auth/me`

Get Current User Info


**Responses:** `200`

### `PATCH` `/api/v1/auth/me`

Update Current User


**Request body** — `application/json` → `UserUpdate`

| Field | Type | Required |
|---|---|---|
| `full_name` | — | — |
| `role` | — | — |
| `is_active` | — | — |


**Responses:** `200`, `422`

### `POST` `/api/v1/auth/register`

Register


**Request body** — `application/json` → `UserCreate`

| Field | Type | Required |
|---|---|---|
| `email` | string | ✅ |
| `password` | string | ✅ |
| `full_name` | — | — |
| `role` | UserRole | — |


**Responses:** `200`, `422`

### `GET` `/api/v1/auth/users`

List Users


**Parameters**

| Name | In | Type | Required |
|---|---|---|---|
| `skip` | query | integer | — |
| `limit` | query | integer | — |


**Responses:** `200`, `422`

### `DELETE` `/api/v1/auth/users/{user_id}`

Delete User


**Parameters**

| Name | In | Type | Required |
|---|---|---|---|
| `user_id` | path | integer | ✅ |


**Responses:** `200`, `422`

### `GET` `/api/v1/auth/users/{user_id}`

Get User


**Parameters**

| Name | In | Type | Required |
|---|---|---|---|
| `user_id` | path | integer | ✅ |


**Responses:** `200`, `422`

### `PATCH` `/api/v1/auth/users/{user_id}`

Update User


**Parameters**

| Name | In | Type | Required |
|---|---|---|---|
| `user_id` | path | integer | ✅ |


**Request body** — `application/json` → `UserUpdate`

| Field | Type | Required |
|---|---|---|
| `full_name` | — | — |
| `role` | — | — |
| `is_active` | — | — |


**Responses:** `200`, `422`


## External Integrations

### `POST` `/api/v1/integrations/accounting/sync`

Sync Accounting Event


وب‌هوک ورودی/خروجی استاندارد برای اتصال به سیستم‌های مالی و حسابداری


**Request body** — `application/json`

**Responses:** `200`, `422`


## Health & Monitoring

### `GET` `/api/v1/health`

Health Check


**Responses:** `200`

### `GET` `/api/v1/health/live`

Liveness Probe


**Responses:** `200`

### `GET` `/api/v1/health/ready`

Readiness Probe


**Responses:** `200`

### `GET` `/api/v1/metrics`

Metrics


**Responses:** `200`


## Multi-Agent Gateway

### `GET` `/api/v1/agents`

List Agents


دریافت لیست ایجنت‌های ثبت‌شده سیستم


**Responses:** `200`

### `POST` `/api/v1/agents/message`

Agent To Agent Message


پروتکل ارتباطی بین ایجنت‌ها (Agent-to-Agent)


**Request body** — `application/json` → `AgentMessage`

| Field | Type | Required |
|---|---|---|
| `sender_id` | string | ✅ |
| `target_id` | string | ✅ |
| `action` | string | ✅ |
| `payload` | object | — |
| `timestamp` | string | — |


**Responses:** `200`, `422`

### `POST` `/api/v1/agents/register`

Register New Agent


تعریف و ثبت داینامیک ایجنت از پنل یا اپلیکیشن‌های دیگر


**Request body** — `application/json` → `AgentConfig`

| Field | Type | Required |
|---|---|---|
| `id` | string | — |
| `name` | string | ✅ |
| `role` | string | ✅ |
| `system_prompt` | string | ✅ |
| `allowed_tools` | array<string> | — |
| `is_active` | boolean | — |
| `metadata` | object | — |


**Responses:** `200`, `422`


## Trading Engine

### `GET` `/api/v1/trading/orders`

List Orders


**Parameters**

| Name | In | Type | Required |
|---|---|---|---|
| `symbol` | query | — | — |


**Responses:** `200`, `422`

### `POST` `/api/v1/trading/orders`

Place Order


**Request body** — `application/json` → `PlaceOrderRequest`

| Field | Type | Required |
|---|---|---|
| `symbol` | string | ✅ |
| `side` | string | ✅ |
| `order_type` | string | ✅ |
| `quantity` | number | ✅ |
| `price` | — | — |
| `stop_price` | — | — |
| `client_order_id` | — | — |


**Responses:** `200`, `422`

### `POST` `/api/v1/trading/orders/batch`

Place Batch Orders


**Request body** — `application/json`

**Responses:** `200`, `422`

### `DELETE` `/api/v1/trading/orders/{order_id}`

Cancel Order


**Parameters**

| Name | In | Type | Required |
|---|---|---|---|
| `order_id` | path | string | ✅ |


**Responses:** `200`, `422`

### `GET` `/api/v1/trading/orders/{order_id}`

Get Order


**Parameters**

| Name | In | Type | Required |
|---|---|---|---|
| `order_id` | path | string | ✅ |


**Responses:** `200`, `422`

### `GET` `/api/v1/trading/portfolio/balances`

Get Balances


**Responses:** `200`

### `GET` `/api/v1/trading/portfolio/pnl`

Get Pnl


**Responses:** `200`

### `GET` `/api/v1/trading/portfolio/positions`

Get Positions


**Responses:** `200`

### `GET` `/api/v1/trading/portfolio/value`

Get Portfolio Value


Total portfolio value quoted in IRT.


**Responses:** `200`


## Untagged

### `POST` `/api/v1/agent/evaluate`

Evaluate


**Request body** — `application/json` → `EvaluateRequest`

| Field | Type | Required |
|---|---|---|
| `wallet_balance_irt` | number | ✅ |
| `market_context` | string | ✅ |


**Responses:** `200`, `422`

### `DELETE` `/api/v1/nobitex/key`

Remove Nobitex Key


Forget the stored API key (kill-switch for exchange access).


**Responses:** `200`

### `POST` `/api/v1/nobitex/save-key`

Save Nobitex Key


**Request body** — `application/json` → `NobitexKeyRequest`

| Field | Type | Required |
|---|---|---|
| `api_key` | string | ✅ |


**Responses:** `200`, `422`

### `GET` `/api/v1/nobitex/status`

Nobitex Status


**Responses:** `200`


---

## Schemas


### `AgentConfig`


| Field | Type | Required |
|---|---|---|
| `id` | string | — |
| `name` | string | ✅ |
| `role` | string | ✅ |
| `system_prompt` | string | ✅ |
| `allowed_tools` | array<string> | — |
| `is_active` | boolean | — |
| `metadata` | object | — |


### `AgentMessage`


| Field | Type | Required |
|---|---|---|
| `sender_id` | string | ✅ |
| `target_id` | string | ✅ |
| `action` | string | ✅ |
| `payload` | object | — |
| `timestamp` | string | — |


### `Body_login_api_v1_auth_login_post`


| Field | Type | Required |
|---|---|---|
| `grant_type` | — | — |
| `username` | string | ✅ |
| `password` | string | ✅ |
| `scope` | string | — |
| `client_id` | — | — |
| `client_secret` | — | — |


### `ChatRequest`


| Field | Type | Required |
|---|---|---|
| `message` | string | ✅ |
| `model` | — | — |
| `use_tools` | boolean | — |
| `stream` | boolean | — |
| `system_prompt` | — | — |


### `CorrelationResponse`


| Field | Type | Required |
|---|---|---|
| `symbol_pairs` | object | ✅ |
| `max_correlation` | number | ✅ |
| `avg_correlation` | number | ✅ |
| `high_correlation_pairs` | array<object> | ✅ |
| `concentration_risk` | number | ✅ |


### `EvaluateRequest`


| Field | Type | Required |
|---|---|---|
| `wallet_balance_irt` | number | ✅ |
| `market_context` | string | ✅ |


### `EvaluateStreamRequest`


| Field | Type | Required |
|---|---|---|
| `wallet_balance_irt` | number | ✅ |
| `market_context` | string | ✅ |


### `HTTPValidationError`


| Field | Type | Required |
|---|---|---|
| `detail` | array<ValidationError> | — |


### `LegacyValidateRequest`


| Field | Type | Required |
|---|---|---|
| `current_balance_irt` | number | ✅ |
| `requested_amount_irt` | number | ✅ |


### `ModelRegisterRequest`


| Field | Type | Required |
|---|---|---|
| `name` | string | ✅ |
| `provider` | string | ✅ |
| `base_url` | string | ✅ |
| `api_key` | — | — |
| `max_tokens` | integer | — |
| `temperature` | number | — |
| `supports_tools` | boolean | — |
| `supports_streaming` | boolean | — |
| `priority` | integer | — |


### `NobitexKeyRequest`


| Field | Type | Required |
|---|---|---|
| `api_key` | string | ✅ |


### `OrderResponseModel`


| Field | Type | Required |
|---|---|---|
| `order_id` | string | ✅ |
| `client_order_id` | — | ✅ |
| `symbol` | string | ✅ |
| `side` | string | ✅ |
| `order_type` | string | ✅ |
| `quantity` | number | ✅ |
| `price` | — | ✅ |
| `status` | string | ✅ |
| `filled_quantity` | number | ✅ |
| `avg_fill_price` | — | ✅ |
| `commission` | number | ✅ |
| `timestamp` | string | ✅ |


### `PlaceOrderRequest`


| Field | Type | Required |
|---|---|---|
| `symbol` | string | ✅ |
| `side` | string | ✅ |
| `order_type` | string | ✅ |
| `quantity` | number | ✅ |
| `price` | — | — |
| `stop_price` | — | — |
| `client_order_id` | — | — |


### `PlaceOrderResponse`


| Field | Type | Required |
|---|---|---|
| `order_id` | string | ✅ |
| `client_order_id` | — | ✅ |
| `symbol` | string | ✅ |
| `side` | string | ✅ |
| `order_type` | string | ✅ |
| `quantity` | number | ✅ |
| `price` | — | ✅ |
| `status` | string | ✅ |
| `filled_quantity` | number | ✅ |
| `avg_fill_price` | — | ✅ |
| `error` | — | — |


### `PositionSizeRequest`


| Field | Type | Required |
|---|---|---|
| `symbol` | string | ✅ |
| `signal_strength` | number | ✅ |
| `volatility` | number | ✅ |
| `portfolio_value` | number | ✅ |
| `current_positions` | object | — |
| `prices` | object | — |
| `max_risk_per_trade` | number | — |


### `PositionSizeResponse`


| Field | Type | Required |
|---|---|---|
| `recommended_size` | number | ✅ |
| `risk_budget_used` | number | ✅ |
| `volatility_adjusted_size` | number | ✅ |
| `signal_adjusted_size` | number | ✅ |


### `RiskMetricsResponse`


| Field | Type | Required |
|---|---|---|
| `metrics` | array<object> | ✅ |
| `overall_level` | string | ✅ |
| `timestamp` | string | ✅ |


### `RiskValidateRequest`


| Field | Type | Required |
|---|---|---|
| `positions` | object | — |
| `prices` | object | — |
| `daily_pnl` | number | — |
| `portfolio_value` | number | ✅ |
| `returns_history` | — | — |


### `StressTestRequest`


| Field | Type | Required |
|---|---|---|
| `positions` | object | — |
| `prices` | object | — |
| `scenarios` | — | — |


### `StressTestResponse`


| Field | Type | Required |
|---|---|---|
| `scenario_name` | string | ✅ |
| `portfolio_value_before` | number | ✅ |
| `portfolio_value_after` | number | ✅ |
| `pnl_impact` | number | ✅ |
| `pnl_pct` | number | ✅ |
| `risk_level` | string | ✅ |
| `details` | object | ✅ |


### `Token`


| Field | Type | Required |
|---|---|---|
| `access_token` | string | ✅ |
| `token_type` | string | — |
| `expires_in` | integer | ✅ |


### `UserCreate`


| Field | Type | Required |
|---|---|---|
| `email` | string | ✅ |
| `password` | string | ✅ |
| `full_name` | — | — |
| `role` | UserRole | — |


### `UserResponse`


| Field | Type | Required |
|---|---|---|
| `id` | integer | ✅ |
| `email` | string | ✅ |
| `full_name` | — | ✅ |
| `role` | UserRole | ✅ |
| `is_active` | boolean | ✅ |
| `is_superuser` | boolean | ✅ |
| `created_at` | string | ✅ |
| `last_login` | — | ✅ |


### `UserRole`


_(free-form object)_


### `UserUpdate`


| Field | Type | Required |
|---|---|---|
| `full_name` | — | — |
| `role` | — | — |
| `is_active` | — | — |


### `VaRResponse`


| Field | Type | Required |
|---|---|---|
| `var_95` | number | ✅ |
| `var_99` | number | ✅ |
| `cvar_95` | number | ✅ |
| `cvar_99` | number | ✅ |
| `confidence_level` | number | ✅ |
| `method` | string | ✅ |
| `timestamp` | string | ✅ |


### `ValidationError`


| Field | Type | Required |
|---|---|---|
| `loc` | array<any> | ✅ |
| `msg` | string | ✅ |
| `type` | string | ✅ |
| `input` | — | — |
| `ctx` | object | — |


---

## نکات قراردادها

- در FastAPI پارامترهای **scalar** یک endpoint `POST` به‌صورت پیش‌فرض *query* هستند و پارامترهای غیرscalar (dict/model) *body*. ترکیب این دو در یک endpoint باعث قرارداد گیج‌کننده می‌شود — `/risk/validate` قبلاً به همین دلیل همیشه `422` می‌داد. همهٔ این endpointها حالا مدل درخواست صریح دارند.
- `/docs` (Swagger UI) فقط وقتی `DEBUG=true` باشد فعال است.
- پاسخ خطاها شامل `correlation_id` است که در هدر `X-Correlation-ID` هم می‌آید.
