"""Release-consistency guards.

The repository advertised five different versions at once (2.2.0 in
`config.py`, "v2.2" and "v1.0.4" in README, 3.1.2 in SECURITY/CONTRIBUTING,
1.0.1 in CHANGELOG, 3.2.3 in the last commit message, 4.0.0 for the web
wizard). Nothing enforced agreement, so documentation and code drifted freely —
which is how 23 endpoints ended up documented but never mounted.

These tests make the version a single source of truth
(`Settings.APP_VERSION`) and fail CI when the docs drift away from it.
"""

import json
import re
from pathlib import Path

import pytest

from app.core.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSION = get_settings().APP_VERSION


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?", VERSION), VERSION


def test_frontend_package_json_matches_backend_version():
    pkg = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert pkg["version"] == VERSION, f"frontend {pkg['version']} != backend {VERSION}"


def test_changelog_has_an_entry_for_this_release():
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^##\s*\[{re.escape(VERSION)}\]", text, re.M), (
        f"CHANGELOG.md has no [{VERSION}] section — add the release notes"
    )


def test_changelog_top_entry_is_this_release():
    """The newest entry must be first, otherwise the file reads as stale."""
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = re.findall(r"^##\s*\[([^\]]+)\]", text, re.M)
    assert headings, "CHANGELOG.md has no version headings"
    assert headings[0] == VERSION, f"top entry is {headings[0]}, expected {VERSION}"


def test_readme_declares_the_current_version():
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert VERSION in text, f"README.md never mentions {VERSION}"


#: Patterns by which a document *declares* its own current version, as opposed
#: to merely mentioning a version as history or as a future target. This is what
#: drifted before: README said "v2.2" in the title and "v1.0.4" in the body
#: while `config.py` said 2.2.0 and the last commit said 3.2.3.
_CURRENT_VERSION_PATTERNS = (
    r"^\*\*(?:نسخه|Version)\s*:?\*\*\s*v?([0-9]+\.[0-9]+\.[0-9]+)",
    # Only the FIRST H1 counts as a self-declaration. Deeper headings are
    # roadmap targets / history ("هدف: v4.0.0"), which are legitimate.
    r"\A#\s[^\n]*?v?([0-9]+\.[0-9]+\.[0-9]+)",
    r"^\[!\[Version\]\(https://img\.shields\.io/badge/version-([0-9.]+)",
    r"^(?:نسخه|Version)\s*:?\s*v?([0-9]+\.[0-9]+\.[0-9]+)",
)


@pytest.mark.parametrize(
    "path",
    ["README.md", "ARCHITECTURE.md", "HANDOFF.md", "ROADMAP.md", "docs/API.md",
     "SECURITY.md", "CONTRIBUTING.md", "INSTALL.md"],
)
def test_docs_declare_the_current_version(path):
    """A doc that *states* its version must state the real one.

    Deliberately does NOT forbid mentioning older or future versions — a
    changelog-style history line or a roadmap target ("v4.0.0") is legitimate.
    Only an explicit "this document is version X" claim is checked.
    """
    full = REPO_ROOT / path
    if not full.exists():
        pytest.skip(f"{path} not present")
    text = full.read_text(encoding="utf-8")

    declared = set()
    for pattern in _CURRENT_VERSION_PATTERNS:
        for m in re.finditer(pattern, text, re.M):
            declared.add(m.group(1))

    # Documents that never state a version are fine (nothing to drift).
    assert declared <= {VERSION}, (
        f"{path} declares version(s) {sorted(declared)} but the release is {VERSION}"
    )


def test_env_example_covers_every_setting_without_a_default():
    """Every required (no-default) Settings field must appear in .env.example.

    A missing entry here is what makes `install.sh` produce a `.env` that the
    backend then refuses to boot with.
    """
    from app.core.config import Settings

    required = {
        name
        for name, field in Settings.model_fields.items()
        if field.is_required()
    }
    # Supplied by docker-compose itself rather than by the operator's .env.
    supplied_by_compose = {"DATABASE_URL", "REDIS_URL"}

    example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    declared = {
        m.group(1)
        for m in re.finditer(r"^\s*([A-Z][A-Z0-9_]*)\s*=", example, re.M)
    }

    missing = required - declared - supplied_by_compose
    assert not missing, f".env.example is missing required keys: {sorted(missing)}"


def test_api_docs_are_up_to_date():
    """`docs/API.md` is generated — CI fails if someone edits code but not docs.

    The handwritten copy had drifted into documenting `POST /api/auth/login`
    (missing the `/v1` prefix) and `POST /api/notifications/send` (an endpoint
    that never existed) while omitting all 34 real routes.
    """
    import importlib.util
    import sys

    script = REPO_ROOT / "backend" / "scripts" / "generate_api_docs.py"
    assert script.exists(), f"generator missing: {script}"

    spec = importlib.util.spec_from_file_location("_gen_api_docs", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_gen_api_docs"] = module
    spec.loader.exec_module(module)

    from app.main import app

    expected = module._render(app.openapi())
    doc = REPO_ROOT / "docs" / "API.md"
    actual = doc.read_text(encoding="utf-8") if doc.exists() else ""

    assert actual == expected, (
        "docs/API.md is stale — run: cd backend && python scripts/generate_api_docs.py"
    )


def test_api_docs_do_not_mention_nonexistent_endpoints():
    """Regression guard for the specific phantom routes in the old hand-written doc."""
    text = (REPO_ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    for phantom in ["/api/notifications/send", "POST /api/auth/login", "/api/health"]:
        assert phantom not in text, f"docs/API.md still advertises phantom route {phantom}"
