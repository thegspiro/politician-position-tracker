import secrets
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from .database import Base

# Media types a source can be rendered as. "webpage" is the neutral default and
# the value every pre-existing source is backfilled to.
MEDIA_TYPES = (
    "webpage",
    "document",
    "video",
    "audio",
    "article",
    "dataset",
)

SOURCE_UID_LENGTH = 12
USER_UID_LENGTH = 12

# Only an owner may manage other accounts. Editors do everything else.
ROLE_OWNER = "owner"
ROLE_EDITOR = "editor"
ROLES = (ROLE_OWNER, ROLE_EDITOR)


def new_user_uid() -> str:
    """A stable public identifier for a user.

    Tokens carry the uid rather than the row id, so a token cannot be made to
    reference a different account by an id being reused after a deletion.
    """
    return secrets.token_urlsafe(9)[:USER_UID_LENGTH]

# Chicago has distinct forms for legislative and legal material. document_type
# selects one; it is only meaningful when media_type is "document".
DOCUMENT_TYPES = (
    "bill",
    "statute",
    "hearing",
    "committee_report",
    "court_opinion",
    "executive_order",
    "other",
)


def new_source_uid() -> str:
    """Generate a short, URL-safe, stable identifier for a source.

    Sources are addressed by uid rather than by primary key because a statement
    edit rewrites its source rows; the uid is what inline citations and
    fragment links point at, so it must survive those edits.
    """
    return secrets.token_urlsafe(9)[:SOURCE_UID_LENGTH]


# Many-to-many association table for statements <-> issues
statement_issues = Table(
    "statement_issues",
    Base.metadata,
    Column("statement_id", Integer, ForeignKey("statements.id", ondelete="CASCADE"), primary_key=True),
    Column("issue_id", Integer, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(USER_UID_LENGTH), nullable=False, unique=True, index=True, default=new_user_uid)
    username = Column(String(150), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=ROLE_EDITOR)
    # Deactivating keeps a user's attribution intact while ending their access;
    # deleting them would orphan every record they created.
    is_active = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    @property
    def is_owner(self) -> bool:
        return self.role == ROLE_OWNER


class Politician(Base):
    __tablename__ = "politicians"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    party = Column(String(100), nullable=False)
    office = Column(String(200), nullable=False)
    state = Column(String(100), nullable=True)
    photo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    statements = relationship("Statement", back_populates="politician", cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    statements = relationship("Statement", secondary=statement_issues, back_populates="issues")


class Statement(Base):
    __tablename__ = "statements"

    id = Column(Integer, primary_key=True, index=True)
    politician_id = Column(Integer, ForeignKey("politicians.id"), nullable=False)
    title = Column(String(500), nullable=False)
    analysis = Column(Text, nullable=False)
    post_url = Column(String(1000), nullable=False)
    post_platform = Column(String(50), nullable=False)  # x, bluesky, truth_social, youtube
    post_content = Column(Text, nullable=True)  # quoted text from the post
    screenshot_url = Column(String(1000), nullable=True)
    post_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Attribution. SET NULL rather than CASCADE: removing an account must not
    # delete the work it produced.
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    politician = relationship("Politician", back_populates="statements")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    issues = relationship("Issue", secondary=statement_issues, back_populates="statements")
    sources = relationship(
        "Source",
        back_populates="statement",
        cascade="all, delete-orphan",
        order_by="(Source.sort_order, Source.id)",
    )


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(
        String(SOURCE_UID_LENGTH),
        nullable=False,
        unique=True,
        index=True,
        default=new_source_uid,
    )
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=False)
    source_type = Column(String(20), nullable=False, default="analysis")  # "post" or "analysis"
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)

    # --- Primary source fields ---
    # How the source should be rendered (see MEDIA_TYPES).
    media_type = Column(String(20), nullable=False, default="webpage", server_default="webpage")
    # Who issued the source: "Congress.gov", "C-SPAN", "FEC".
    publisher = Column(String(200), nullable=True)
    published_date = Column(DateTime, nullable=True)
    # Verbatim passage being relied on.
    excerpt = Column(Text, nullable=True)
    # Where in the source the excerpt lives: "p. 14", "sec. 203", "01:23:45".
    locator = Column(String(100), nullable=True)
    # --- Citation fields ---
    # Ordered list of {"family", "given"} or {"literal"} objects. JSON rather
    # than a child table because authors are only ever read as an ordered list
    # with their source, never queried across sources. The type maps to a native
    # JSON column on MySQL and to serialised TEXT on SQLite.
    #
    # Left nullable with no server default: MySQL before 8.0.13 rejects DEFAULT
    # on a JSON column. Readers normalise NULL to an empty list.
    authors = Column(JSON, nullable=True)
    # The larger work the source sits in: a newspaper, site, or journal.
    container_title = Column(String(300), nullable=True)
    edition = Column(String(100), nullable=True)

    # --- Legislative and legal material ---
    document_type = Column(String(40), nullable=True)
    bill_number = Column(String(50), nullable=True)
    congress_number = Column(Integer, nullable=True)
    congress_session = Column(String(20), nullable=True)
    committee = Column(String(300), nullable=True)
    report_number = Column(String(50), nullable=True)

    # Snapshot used when the original URL rots.
    archive_url = Column(String(1000), nullable=True)
    archived_at = Column(DateTime, nullable=True)
    # When the original was last confirmed to say what is quoted.
    retrieved_at = Column(DateTime, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    statement = relationship("Statement", back_populates="sources")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
