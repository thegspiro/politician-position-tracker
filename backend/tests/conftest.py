"""Test configuration.

``app.main`` has import-time side effects: it creates the upload directory and
registers the SPA catch-all route only when ``backend/static`` exists. Both are
set up here, against temporary locations where possible, before the module is
imported by any test.

The schema is owned by Alembic, so the test database is built by running the
migrations rather than by ``create_all``. That means every test run exercises
the same upgrade path a deployment takes.
"""

import os
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BACKEND_DIR / "static"

_TMP = Path(tempfile.mkdtemp(prefix="ppt-tests-"))
os.environ.setdefault("UPLOAD_DIR", str(_TMP / "uploads"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP / 'test.db'}")

# Credentials must be set before app.auth is imported: it refuses to load on a
# published default value.
TEST_ADMIN_PASSWORD = "test-admin-password"
os.environ.setdefault("ADMIN_PASSWORD", TEST_ADMIN_PASSWORD)
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-used-anywhere-real")

# The SPA catch-all is only registered when the built frontend is present. In a
# source checkout it is not, so a minimal stand-in is created at the same path
# the Docker build writes to. It is gitignored and overwritten by real builds.
(STATIC_DIR / "assets").mkdir(parents=True, exist_ok=True)
_INDEX = STATIC_DIR / "index.html"
if not _INDEX.exists():
    _INDEX.write_text("<html>spa</html>")
_APP_JS = STATIC_DIR / "assets" / "app.js"
if not _APP_JS.exists():
    _APP_JS.write_text("console.log('app');")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402


def alembic_config(database_url: str) -> Config:
    """Build an Alembic config pointed at ``database_url``."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


# Bring the shared test database to head once for the whole session.
command.upgrade(alembic_config(os.environ["DATABASE_URL"]), "head")
