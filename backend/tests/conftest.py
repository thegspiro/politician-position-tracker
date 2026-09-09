"""Test configuration.

``app.main`` has import-time side effects: it creates the upload directory,
creates the database schema, and registers the SPA catch-all route only when
``backend/static`` exists. All three are set up here, against temporary
locations where possible, before the module is imported by any test.
"""

import os
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BACKEND_DIR / "static"

_TMP = Path(tempfile.mkdtemp(prefix="ppt-tests-"))
os.environ.setdefault("UPLOAD_DIR", str(_TMP / "uploads"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP / 'test.db'}")

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
