"""Site-level configuration read from the environment.

Kept apart from app.main so routers can import it without a circular import.
"""

import os

from .citations import CITATION_STYLES, SITE_STYLE_NOTES

SITE_NAME = os.environ.get("SITE_NAME", "Politician Tracker")

_configured_style = os.environ.get("CITATION_STYLE", SITE_STYLE_NOTES).strip()
# An unrecognised value falls back rather than failing the boot: a typo here
# should not take the site down, and the default is always valid.
CITATION_STYLE = (
    _configured_style if _configured_style in CITATION_STYLES else SITE_STYLE_NOTES
)
