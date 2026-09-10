"""Submit source URLs to the Internet Archive's Wayback Machine.

A citation is only as durable as the page it points at, so a source without an
archive snapshot is one deletion away from being unverifiable. When enabled,
saving a source submits its URL for capture and records the resulting snapshot
URL and date.

Disabled by default: the container must reach the public internet for this to
work, and an air-gapped or LAN-only deployment should not spend every save
waiting on a network call it cannot make.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

SAVE_ENDPOINT = "https://web.archive.org/save/"
WAYBACK_PREFIX = "https://web.archive.org/web/"

ARCHIVE_ENABLED = os.environ.get("ARCHIVE_ENABLED", "").lower() in {"1", "true", "yes"}
ARCHIVE_TIMEOUT_SECONDS = float(os.environ.get("ARCHIVE_TIMEOUT_SECONDS", "30"))

# Only these schemes are ever submitted. Source URLs are already validated at
# the API edge; this is a second check because the value reaches an outbound
# request.
SUBMITTABLE_SCHEMES = ("http", "https")


@dataclass(frozen=True)
class ArchiveResult:
    """The outcome of one capture attempt."""

    url: str | None
    timestamp: datetime | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.url is not None


def is_submittable(url: str | None) -> bool:
    """Whether a URL may be sent to the Wayback Machine.

    Already-archived URLs are refused: re-submitting a snapshot would archive
    the archive rather than the original.
    """
    if not url:
        return False
    candidate = url.strip()
    if candidate.startswith(WAYBACK_PREFIX):
        return False
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False
    return parsed.scheme.lower() in SUBMITTABLE_SCHEMES and bool(parsed.netloc)


def _snapshot_url_from_response(response: httpx.Response, source_url: str) -> str | None:
    """Recover the snapshot URL from a save response.

    The service reports the capture in a Content-Location header, and otherwise
    redirects to the snapshot, so the final request URL is used as a fallback.
    """
    content_location = response.headers.get("content-location")
    if content_location:
        if content_location.startswith("http"):
            return content_location
        return f"https://web.archive.org{content_location}"

    final_url = str(response.url)
    if final_url.startswith(WAYBACK_PREFIX):
        return final_url

    # The save endpoint echoes the target back in its own URL on success.
    if final_url.startswith(SAVE_ENDPOINT) and final_url != SAVE_ENDPOINT + source_url:
        return None
    return None


def archive_url(url: str, *, timeout: float | None = None) -> ArchiveResult:
    """Submit one URL for capture.

    Returns a result rather than raising: a failed capture must never fail the
    save that triggered it. The source keeps whatever archive details it had.
    """
    if not is_submittable(url):
        return ArchiveResult(None, None, error="URL is not submittable")

    deadline = ARCHIVE_TIMEOUT_SECONDS if timeout is None else timeout
    try:
        with httpx.Client(timeout=deadline, follow_redirects=True) as client:
            response = client.get(
                SAVE_ENDPOINT + url,
                headers={"User-Agent": "politician-position-tracker/1.0"},
            )
    except httpx.HTTPError as exc:
        logger.warning("Wayback save failed for %s: %s", url, exc)
        return ArchiveResult(None, None, error=str(exc))

    if response.status_code >= 400:
        logger.warning(
            "Wayback save returned %s for %s", response.status_code, url
        )
        return ArchiveResult(
            None, None, error=f"archive service returned {response.status_code}"
        )

    snapshot = _snapshot_url_from_response(response, url)
    if not snapshot:
        logger.warning("Wayback save gave no snapshot URL for %s", url)
        return ArchiveResult(None, None, error="no snapshot URL in response")

    return ArchiveResult(snapshot, datetime.now(timezone.utc).replace(tzinfo=None))
