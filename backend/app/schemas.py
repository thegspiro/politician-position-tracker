from datetime import datetime
from typing import Generic, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator

from .models import MEDIA_TYPES

T = TypeVar("T")

SOURCE_TYPES = ("post", "analysis")

# Only these schemes may be stored for a value that is rendered as a link. A
# "javascript:" or "data:" URL placed in an href executes in the visitor's
# browser, so the scheme is checked at the edge rather than at render time.
ALLOWED_URL_SCHEMES = ("http", "https")


def validate_link(value: str, field_name: str) -> str:
    """Reject anything that is not an absolute http(s) URL."""
    candidate = value.strip()
    if not candidate:
        raise ValueError(f"{field_name} must not be empty")
    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        raise ValueError(
            f"{field_name} must be an http:// or https:// URL"
        )
    if not parsed.netloc:
        raise ValueError(f"{field_name} must include a host")
    return candidate


# --- Paginated Response ---
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int


# --- Source ---
class SourceBase(BaseModel):
    source_type: str = "analysis"  # "post" or "analysis"
    title: str
    url: str
    description: str | None = None

    # --- Primary source fields ---
    media_type: str = "webpage"
    publisher: str | None = None
    published_date: datetime | None = None
    excerpt: str | None = None
    locator: str | None = None
    archive_url: str | None = None
    archived_at: datetime | None = None
    retrieved_at: datetime | None = None
    sort_order: int = 0

    @field_validator("source_type")
    @classmethod
    def _check_source_type(cls, value: str) -> str:
        if value not in SOURCE_TYPES:
            raise ValueError(f"source_type must be one of {', '.join(SOURCE_TYPES)}")
        return value

    @field_validator("media_type")
    @classmethod
    def _check_media_type(cls, value: str) -> str:
        if value not in MEDIA_TYPES:
            raise ValueError(f"media_type must be one of {', '.join(MEDIA_TYPES)}")
        return value

    @field_validator("url")
    @classmethod
    def _check_url(cls, value: str) -> str:
        return validate_link(value, "url")

    @field_validator("archive_url")
    @classmethod
    def _check_archive_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return validate_link(value, "archive_url")


class SourceCreate(SourceBase):
    # Supplied when editing an existing source so its stable identifier -- and
    # therefore any citation pointing at it -- survives the update. Omitted for
    # a new source, which is assigned one on insert.
    uid: str | None = None


class SourceOut(SourceBase):
    id: int
    uid: str

    model_config = {"from_attributes": True}


# --- Issue ---
class IssueBase(BaseModel):
    name: str
    description: str | None = None


class IssueCreate(IssueBase):
    pass


class IssueOut(IssueBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Politician ---
class PoliticianBase(BaseModel):
    name: str
    party: str
    office: str
    state: str | None = None
    photo_url: str | None = None


class PoliticianCreate(PoliticianBase):
    pass


class PoliticianOut(PoliticianBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Statement ---
class StatementBase(BaseModel):
    title: str
    analysis: str
    post_url: str
    post_platform: str
    post_content: str | None = None
    screenshot_url: str | None = None
    post_date: datetime | None = None

    @field_validator("post_url")
    @classmethod
    def _check_post_url(cls, value: str) -> str:
        return validate_link(value, "post_url")


class StatementCreate(StatementBase):
    politician_id: int
    issue_ids: list[int] = []
    sources: list[SourceCreate] = []


class StatementUpdate(StatementBase):
    politician_id: int
    issue_ids: list[int] = []
    sources: list[SourceCreate] = []


class StatementOut(StatementBase):
    id: int
    politician_id: int
    created_at: datetime
    updated_at: datetime
    politician: PoliticianOut
    issues: list[IssueOut] = []
    sources: list[SourceOut] = []

    model_config = {"from_attributes": True}


class StatementListOut(StatementBase):
    id: int
    politician_id: int
    created_at: datetime
    updated_at: datetime
    politician: PoliticianOut
    issues: list[IssueOut] = []

    model_config = {"from_attributes": True}


# --- Politician detail with statements ---
class PoliticianDetailOut(PoliticianOut):
    statements: list[StatementListOut] = []

    model_config = {"from_attributes": True}


# --- Issue detail with statements ---
class IssueDetailOut(IssueOut):
    statements: list[StatementListOut] = []

    model_config = {"from_attributes": True}
