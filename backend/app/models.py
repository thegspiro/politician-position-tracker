from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from .database import Base


# Many-to-many association table for statements <-> issues
statement_issues = Table(
    "statement_issues",
    Base.metadata,
    Column("statement_id", Integer, ForeignKey("statements.id", ondelete="CASCADE"), primary_key=True),
    Column("issue_id", Integer, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True),
)


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

    politician = relationship("Politician", back_populates="statements")
    issues = relationship("Issue", secondary=statement_issues, back_populates="statements")
    sources = relationship("Source", back_populates="statement", cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=False)
    source_type = Column(String(20), nullable=False, default="analysis")  # "post" or "analysis"
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)

    statement = relationship("Statement", back_populates="sources")
