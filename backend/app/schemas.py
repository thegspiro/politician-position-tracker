from datetime import datetime
from typing import Generic, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator, model_validator

from . import citations
from .models import DOCUMENT_TYPES, MEDIA_TYPES, ROLES
from .passwords import MIN_PASSWORD_LENGTH, validate_password_strength

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


# --- Users ---
def _check_password(value: str) -> str:
    try:
        validate_password_strength(value)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    return value


def _check_role(value: str) -> str:
    if value not in ROLES:
        raise ValueError(f"role must be one of {', '.join(ROLES)}")
    return value


def _check_username(value: str) -> str:
    username = value.strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if len(username) > 150:
        raise ValueError("Username must be at most 150 characters")
    if not all(char.isalnum() or char in "._-@" for char in username):
        raise ValueError(
            "Username may contain only letters, digits and the characters . _ - @"
        )
    return username


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    role: str = "editor"
    is_active: bool = True

    _validate_username = field_validator("username")(classmethod(lambda cls, v: _check_username(v)))
    _validate_password = field_validator("password")(classmethod(lambda cls, v: _check_password(v)))
    _validate_role = field_validator("role")(classmethod(lambda cls, v: _check_role(v)))


class UserUpdate(BaseModel):
    """Every field optional: absent means "leave as is"."""

    username: str | None = None
    password: str | None = None
    display_name: str | None = None
    role: str | None = None
    is_active: bool | None = None

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str | None) -> str | None:
        return None if value is None else _check_username(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        return _check_password(value)

    @field_validator("role")
    @classmethod
    def _validate_role(cls, value: str | None) -> str | None:
        return None if value is None else _check_role(value)


class UserOut(BaseModel):
    uid: str
    username: str
    display_name: str | None = None
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_validator("is_active", mode="before")
    @classmethod
    def _coerce_is_active(cls, value):
        """Stored as an integer so the column is portable across backends."""
        return bool(value)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    _validate_new = field_validator("new_password")(
        classmethod(lambda cls, v: _check_password(v))
    )


MINIMUM_PASSWORD_LENGTH = MIN_PASSWORD_LENGTH


# --- Attribution ---
class AttributionOut(BaseModel):
    """Who a record is attributed to, as shown alongside it."""

    uid: str
    username: str
    display_name: str | None = None

    model_config = {"from_attributes": True}


# --- Source ---
class Author(BaseModel):
    """A personal name, or a corporate one via ``literal``.

    Names are kept structured because Chicago inverts the lead author in a
    bibliography ("Doe, Jane") but not in a note, and never inverts a corporate
    name.
    """

    given: str | None = None
    family: str | None = None
    literal: str | None = None

    @model_validator(mode="after")
    def _require_a_name(self) -> "Author":
        if not any(
            (value or "").strip() for value in (self.given, self.family, self.literal)
        ):
            raise ValueError("an author needs given/family or literal")
        if (self.literal or "").strip() and (
            (self.given or "").strip() or (self.family or "").strip()
        ):
            raise ValueError("use either literal or given/family, not both")
        return self


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

    # --- Citation fields ---
    authors: list[Author] = []
    container_title: str | None = None
    edition: str | None = None

    # --- Legislative and legal material ---
    document_type: str | None = None
    bill_number: str | None = None
    congress_number: int | None = None
    congress_session: str | None = None
    committee: str | None = None
    report_number: str | None = None

    @field_validator("authors", mode="before")
    @classmethod
    def _normalise_authors(cls, value):
        """The database column is nullable; absent authors read as an empty list.

        The column is left nullable because MySQL before 8.0.13 rejects a
        DEFAULT on a JSON column, so NULL is the only usable "not set" value.
        """
        return [] if value is None else value

    @field_validator("document_type")
    @classmethod
    def _check_document_type(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        if value not in DOCUMENT_TYPES:
            raise ValueError(
                f"document_type must be one of {', '.join(DOCUMENT_TYPES)}"
            )
        return value

    @field_validator("congress_number")
    @classmethod
    def _check_congress_number(cls, value: int | None) -> int | None:
        if value is not None and not 1 <= value <= 999:
            raise ValueError("congress_number must be between 1 and 999")
        return value

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


class CitationForm(BaseModel):
    """One rendered citation: plain text for copying, spans for display."""

    text: str
    spans: list[dict]


class CitationSet(BaseModel):
    note: CitationForm
    bibliography: CitationForm
    author_date_citation: CitationForm
    author_date_reference: CitationForm


class SourceOut(SourceBase):
    id: int
    uid: str
    created_by: AttributionOut | None = None
    updated_by: AttributionOut | None = None
    # Rendered server-side so the Chicago rules live in exactly one place and
    # the exported files cannot drift from what the page displays.
    citations: CitationSet | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _render_citations(self) -> "SourceOut":
        if self.citations is None:
            data = citations.CitationInput(
                title=self.title,
                url=self.url,
                authors=[a.model_dump() for a in self.authors],
                container_title=self.container_title,
                publisher=self.publisher,
                published_date=self.published_date,
                accessed=self.retrieved_at,
                locator=self.locator,
                edition=self.edition,
                media_type=self.media_type,
                document_type=self.document_type,
                bill_number=self.bill_number,
                congress_number=self.congress_number,
                congress_session=self.congress_session,
                committee=self.committee,
                report_number=self.report_number,
            )
            object.__setattr__(self, "citations", CitationSet(**citations.render_all(data)))
        return self


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
    created_by: AttributionOut | None = None
    updated_by: AttributionOut | None = None

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
