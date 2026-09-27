"""End-to-end wiring tests.

These exist because the v1 router surface was silently disconnected from the
application: `app.api.v1.api_router` was built as an import side-effect and then
thrown away, so 23 endpoints documented in README/HANDOFF/docs returned 404.
There was also no CORS middleware at all, and the auth chain had two latent
defects (passlib+bcrypt raising on every hash, and a `str` user id reaching an
INTEGER primary key) that no mocked test could catch.

Nothing here is mocked at the HTTP boundary: a real SQLite database is created,
real users are inserted with real bcrypt hashes, and a real JWT round-trip is
asserted through the full ASGI stack.

Runs with zero external services (no Postgres, no Redis, no Ollama, no network).
"""

import os

os.environ.setdefault("API_SECRET_KEY", "wiring-test-secret-key-that-is-long-enough-32")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import importlib
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401 - registers models on Base.metadata
from app.core.auth import get_password_hash, verify_password
from app.db.models import User, UserRole
from app.db.session import Base, get_async_session
from app.main import app

ADMIN_EMAIL = "wiring-admin@aark.test"
ADMIN_PASSWORD = "Str0ng!WiringPass"
TRADER_EMAIL = "wiring-trader@aark.test"
TRADER_PASSWORD = "Str0ng!TraderPass"


# --------------------------------------------------------------------------- #
# Fixtures — one event loop for the whole request path (ASGITransport, no
# TestClient portal), so the async SQLite engine is never cross-loop.
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def db_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'wiring.sqlite'}", future=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        session.add_all(
            [
                User(
                    email=ADMIN_EMAIL,
                    hashed_password=get_password_hash(ADMIN_PASSWORD),
                    full_name="Wiring Admin",
                    role=UserRole.ADMIN,
                    is_active=True,
                    is_superuser=True,
                ),
                User(
                    email=TRADER_EMAIL,
                    hashed_password=get_password_hash(TRADER_PASSWORD),
                    full_name="Wiring Trader",
                    role=UserRole.TRADER,
                    is_active=True,
                    is_superuser=False,
                ),
            ]
        )
        await session.commit()

    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_factory) -> AsyncIterator[AsyncClient]:
    async def _override() -> AsyncIterator[AsyncSession]:
        async with db_factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://wiring.test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_async_session, None)


async def _login(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        content=f"username={email}&password={password}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------- #
# 1. The v1 surface is actually mounted
# --------------------------------------------------------------------------- #

REQUIRED_PATHS = {
    "/api/v1/health",
    "/api/v1/health/live",
    "/api/v1/health/ready",
    "/api/v1/metrics",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/me",
    "/api/v1/auth/users",
    "/api/v1/ai/models",
    "/api/v1/ai/tools",
    "/api/v1/ai/agent/chat",
    "/api/v1/trading/orders",
    "/api/v1/trading/portfolio/balances",
    "/api/v1/trading/portfolio/positions",
    "/api/v1/trading/portfolio/pnl",
    "/api/v1/trading/portfolio/value",
    "/api/v1/risk/var",
    "/api/v1/risk/stress-test",
    "/api/v1/risk/correlation",
    "/api/v1/risk/validate",
    "/api/v1/risk/position-size",
    "/api/v1/risk/summary",
    "/api/v1/agent/evaluate",
    "/api/v1/nobitex/status",
}


def test_every_documented_endpoint_is_mounted():
    """Guards the regression that made 23 documented endpoints 404."""
    live = set(app.openapi()["paths"])
    missing = REQUIRED_PATHS - live
    assert not missing, f"endpoints advertised in docs but not mounted: {sorted(missing)}"


def _walk_routes(routes, prefix=""):
    """Flatten an APIRouter tree, including FastAPI's lazy include wrappers."""
    out = []
    for r in routes:
        cls = type(r).__name__
        if cls == "_IncludedRouter":
            ctx = getattr(r, "include_context", None)
            sub = prefix + (getattr(ctx, "prefix", "") or "")
            orig = getattr(r, "original_router", None)
            if orig is not None:
                out += _walk_routes(getattr(orig, "routes", []), sub)
            continue
        if cls == "Mount":
            continue
        path = getattr(r, "path", None)
        if path is not None:
            out.append((prefix + path, cls, sorted(getattr(r, "methods", None) or [])))
    return out


def test_websocket_route_is_mounted():
    """WebSocket routes never appear in OpenAPI — assert on the router tree."""
    flat = _walk_routes(app.routes)
    ws_paths = [path for path, cls, _ in flat if "WebSocket" in cls]
    assert "/api/v1/ws/ws" in ws_paths, f"ws route missing, got {ws_paths}"


def test_route_count_matches_openapi_plus_websocket():
    """Cheap structural guard: nothing is silently dropped during include."""
    flat = _walk_routes(app.routes)
    http = {path for path, cls, methods in flat if methods}
    schema = set(app.openapi()["paths"])
    assert schema <= http, f"openapi paths not routable: {sorted(schema - http)}"


# --------------------------------------------------------------------------- #
# 2. Auth chain works for real (bcrypt + JWT + INTEGER pk lookup)
# --------------------------------------------------------------------------- #


def test_password_hash_roundtrip():
    """passlib+bcrypt used to raise ValueError on every hash() call."""
    hashed = get_password_hash(ADMIN_PASSWORD)
    assert hashed.startswith("$2")
    assert verify_password(ADMIN_PASSWORD, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_password_hash_handles_oversized_secret():
    """bcrypt>=4.1 raises past 72 bytes; we truncate deterministically."""
    long_pw = "A" * 200
    hashed = get_password_hash(long_pw)
    assert verify_password(long_pw, hashed) is True


def test_verify_password_never_raises_on_garbage():
    assert verify_password("x", "") is False
    assert verify_password("x", "not-a-bcrypt-hash") is False


async def test_login_returns_jwt_with_correct_expiry(client):
    token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert token.count(".") == 2

    from jose import jwt

    from app.core.config import get_settings

    payload = jwt.decode(token, get_settings().API_SECRET_KEY, algorithms=["HS256"])
    assert payload["role"] == "admin"
    assert int(payload["exp"]) - int(payload["iat"]) == 1800  # documented 30 min


async def test_login_rejects_wrong_password(client):
    res = await client.post(
        "/api/v1/auth/login",
        content=f"username={ADMIN_EMAIL}&password=not-the-password",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 401


async def test_me_resolves_user_from_string_sub(client):
    """`sub` is issued as str(user.id); the DB lookup needs an int."""
    token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    res = await client.get("/api/v1/auth/me", headers=_bearer(token))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"
    assert isinstance(body["id"], int)


async def test_garbage_token_is_rejected(client):
    res = await client.get("/api/v1/auth/me", headers=_bearer("a.b.c"))
    assert res.status_code == 401


async def test_non_numeric_sub_is_rejected(client):
    """A hand-crafted token with sub='abc' must 401, not 500."""
    from datetime import timedelta

    from jose import jwt

    from app.core.config import get_settings

    forged = jwt.encode(
        {"sub": "not-an-int"},
        get_settings().API_SECRET_KEY,
        algorithm="HS256",
    )
    del timedelta
    res = await client.get("/api/v1/auth/me", headers=_bearer(forged))
    assert res.status_code == 401


# --------------------------------------------------------------------------- #
# 3. Protected surface is protected; public surface is public
# --------------------------------------------------------------------------- #

PROTECTED = [
    ("GET", "/api/v1/trading/orders"),
    ("GET", "/api/v1/trading/portfolio/balances"),
    ("GET", "/api/v1/risk/summary"),
    ("GET", "/api/v1/ai/models"),
    ("GET", "/api/v1/auth/me"),
]

PUBLIC = [
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/health/live"),
    ("GET", "/api/v1/nobitex/status"),
    ("GET", "/api/v1/agents"),
]


@pytest.mark.parametrize("method,path", PROTECTED)
async def test_protected_endpoints_require_credentials(client, method, path):
    assert (await client.request(method, path)).status_code == 401, path


@pytest.mark.parametrize("method,path", PUBLIC)
async def test_public_endpoints_stay_open(client, method, path):
    assert (await client.request(method, path)).status_code == 200, path


async def test_trader_cannot_list_users(client):
    """RBAC: /auth/users is ADMIN-only."""
    trader = await _login(client, TRADER_EMAIL, TRADER_PASSWORD)
    res = await client.get("/api/v1/auth/users", headers=_bearer(trader))
    assert res.status_code == 403

    admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    res = await client.get("/api/v1/auth/users", headers=_bearer(admin))
    assert res.status_code == 200


async def test_register_requires_admin(client):
    """Anonymous registration must not be possible on a trading platform."""
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": "anon@aark-kernel.dev", "password": "Str0ng!AnonPass", "role": "admin"},
    )
    assert res.status_code == 401


async def test_admin_can_register_a_new_user(client):
    admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": "new-trader@aark-kernel.dev", "password": "Str0ng!NewPass", "role": "trader"},
        headers=_bearer(admin),
    )
    assert res.status_code == 200, res.text
    assert res.json()["email"] == "new-trader@aark-kernel.dev"

    # and the new user can immediately log in (proves the bcrypt hash is usable)
    assert await _login(client, "new-trader@aark-kernel.dev", "Str0ng!NewPass")


# --------------------------------------------------------------------------- #
# 4. CORS is actually registered
# --------------------------------------------------------------------------- #


async def test_cors_allows_configured_origin(client):
    """BACKEND_CORS_ORIGINS was dead config — no CORSMiddleware existed."""
    res = await client.get("/api/v1/health/live", headers={"Origin": "http://localhost:3000"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"


async def test_cors_preflight(client):
    res = await client.options(
        "/api/v1/health/live",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"


async def test_cors_rejects_unknown_origin(client):
    res = await client.get("/api/v1/health/live", headers={"Origin": "http://evil.example"})
    assert res.headers.get("access-control-allow-origin") is None


# --------------------------------------------------------------------------- #
# 5. Risk engine: single source of truth + live endpoints
# --------------------------------------------------------------------------- #


def test_risk_profile_is_not_duplicated():
    """`advanced` used to re-define RiskProfile/DeterministicRiskEngine."""
    from app.risk_engine import advanced, evaluator

    assert advanced.RiskProfile is evaluator.RiskProfile
    assert advanced.DeterministicRiskEngine is evaluator.DeterministicRiskEngine


async def test_risk_validate_endpoint_returns_metrics(client):
    admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    res = await client.post(
        "/api/v1/risk/validate",
        json={"positions": {}, "prices": {}, "daily_pnl": 0, "portfolio_value": 10_000_000},
        headers=_bearer(admin),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["overall_level"] in {"low", "medium", "high", "critical"}
    assert isinstance(body["metrics"], list) and body["metrics"]


async def test_risk_var_requires_portfolio_value(client):
    """`portfolio_value` is a required query param — must 422, not 500."""
    admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    res = await client.get("/api/v1/risk/var", headers=_bearer(admin))
    assert res.status_code == 422

    res = await client.get("/api/v1/risk/var?portfolio_value=100000", headers=_bearer(admin))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["cvar_95"] >= body["var_95"]


async def test_risk_legacy_validate_matches_agent_path(client):
    """/risk/legacy/validate must agree with DeterministicRiskEngine directly."""
    from app.core.config import get_settings
    from app.risk_engine.evaluator import DeterministicRiskEngine, RiskProfile

    settings = get_settings()
    profile = RiskProfile(
        max_portfolio_allocation_irt=settings.MAX_PORTFOLIO_ALLOCATION_IRT,
        max_single_trade_pct=settings.MAX_SINGLE_TRADE_PCT,
        max_daily_loss_pct=settings.MAX_DAILY_LOSS_PCT,
    )

    admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    for balance, amount in [
        (10_000_000, 1_000_000),   # within the 20% single-trade cap -> approved
        (10_000_000, 5_000_000),   # above the cap -> rejected
        (10_000_000, -1),          # negative amount -> rejected
        (0, 0),                    # empty wallet -> approved no-op
    ]:
        res = await client.post(
            "/api/v1/risk/legacy/validate",
            json={"current_balance_irt": balance, "requested_amount_irt": amount},
            headers=_bearer(admin),
        )
        assert res.status_code == 200, res.text
        expected_ok, expected_msg = DeterministicRiskEngine.validate_order(profile, balance, amount)
        assert res.json()["approved"] is expected_ok
        assert res.json()["message"] == expected_msg


async def test_risk_legacy_validate_rejects_negative_balance(client):
    """A negative wallet balance is a malformed request, not a risk decision."""
    admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    res = await client.post(
        "/api/v1/risk/legacy/validate",
        json={"current_balance_irt": -5, "requested_amount_irt": 0},
        headers=_bearer(admin),
    )
    assert res.status_code == 422


# --------------------------------------------------------------------------- #
# 6. The agent brain is a singleton
# --------------------------------------------------------------------------- #


def test_single_shared_agent_brain():
    """main.py and api/v1/ai.py each built their own AgentBrain()."""
    from app.api.v1 import ai
    from app.core.agent import brain
    from app.main import brain as main_brain

    assert brain is main_brain
    assert ai.brain is brain


# --------------------------------------------------------------------------- #
# 7. Vault round-trip (single source of truth, 0600/0700)
# --------------------------------------------------------------------------- #


@pytest.fixture
def vault(tmp_path, monkeypatch):
    """A freshly-imported app.core.vault pointed at a throwaway directory."""
    vault_dir = tmp_path / "vault"
    monkeypatch.setenv("AARK_VAULT_DIR", str(vault_dir))
    module = importlib.reload(importlib.import_module("app.core.vault"))
    yield module, vault_dir
    monkeypatch.delenv("AARK_VAULT_DIR", raising=False)
    importlib.reload(importlib.import_module("app.core.vault"))


def test_vault_roundtrip_and_permissions(vault):
    module, vault_dir = vault

    assert module.get_vault_token() == ""
    module.save_vault_token("k" * 40)
    assert module.get_vault_token() == "k" * 40

    file_mode = (vault_dir / "nobitex.vault").stat().st_mode & 0o777
    assert file_mode == 0o600, f"vault must be 0600, got {oct(file_mode)}"

    dir_mode = vault_dir.stat().st_mode & 0o777
    assert dir_mode == 0o700, f"vault dir must be 0700, got {oct(dir_mode)}"

    assert module.clear_vault_token() is True
    assert module.get_vault_token() == ""
    assert module.clear_vault_token() is False


def test_vault_survives_corrupt_file(vault):
    module, vault_dir = vault
    vault_dir.mkdir(parents=True, exist_ok=True)
    (vault_dir / "nobitex.vault").write_text("{not json", encoding="utf-8")
    assert module.get_vault_token() == ""  # must not raise


def test_vault_overwrite_leaves_no_temp_file(vault):
    module, vault_dir = vault
    module.save_vault_token("a" * 40)
    module.save_vault_token("b" * 40)
    assert module.get_vault_token() == "b" * 40
    assert sorted(p.name for p in vault_dir.iterdir()) == ["nobitex.vault"]


# --------------------------------------------------------------------------- #
# 8. Admin bootstrap breaks the fresh-install deadlock
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def bootstrap_env(tmp_path, monkeypatch):
    """Point app.db.init_db's session factory at a real SQLite file."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'boot.sqlite'}", future=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    import app.db.init_db as init_db_module
    import app.db.session as session_module

    original = session_module.async_session_factory
    session_module.async_session_factory = factory
    init_db_module.async_session_factory = factory

    yield factory, session_module

    session_module.async_session_factory = original
    init_db_module.async_session_factory = original
    await engine.dispose()


async def test_bootstrap_admin_creates_superuser(bootstrap_env, monkeypatch):
    factory, _ = bootstrap_env
    from app.db.init_db import bootstrap_admin

    monkeypatch.setenv("ADMIN_EMAIL", "Boot@AARK.Test")
    monkeypatch.setenv("ADMIN_PASSWORD", "Str0ng!BootPass")

    await bootstrap_admin()
    await bootstrap_admin()  # idempotent — must not raise on duplicate email

    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.email == "boot@aark.test"))
        ).scalar_one()

    assert user.role == UserRole.ADMIN
    assert user.is_superuser is True
    assert user.is_active is True
    assert verify_password("Str0ng!BootPass", user.hashed_password)


async def test_bootstrap_admin_promotes_existing_user(bootstrap_env, monkeypatch):
    factory, _ = bootstrap_env
    from app.db.init_db import bootstrap_admin

    async with factory() as session:
        session.add(
            User(
                email="promote@aark.test",
                hashed_password=get_password_hash("Str0ng!Existing"),
                role=UserRole.VIEWER,
                is_active=False,
            )
        )
        await session.commit()

    monkeypatch.setenv("ADMIN_EMAIL", "promote@aark.test")
    monkeypatch.setenv("ADMIN_PASSWORD", "irrelevant-not-used")
    await bootstrap_admin()

    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.email == "promote@aark.test"))
        ).scalar_one()

    assert user.role == UserRole.ADMIN
    assert user.is_active is True
    # the operator's existing password must NOT be overwritten
    assert verify_password("Str0ng!Existing", user.hashed_password)


async def test_bootstrap_admin_skipped_without_env(bootstrap_env, monkeypatch):
    """CI/tests set no ADMIN_* — bootstrap must be a silent no-op."""
    factory, _ = bootstrap_env
    from app.db.init_db import bootstrap_admin

    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    await bootstrap_admin()

    async with factory() as session:
        assert (await session.execute(select(User))).scalars().all() == []


async def test_bootstrap_admin_refuses_weak_password(bootstrap_env, monkeypatch):
    factory, _ = bootstrap_env
    from app.db.init_db import bootstrap_admin

    monkeypatch.setenv("ADMIN_EMAIL", "weak@aark.test")
    monkeypatch.setenv("ADMIN_PASSWORD", "short")
    await bootstrap_admin()

    async with factory() as session:
        assert (await session.execute(select(User))).scalars().all() == []
