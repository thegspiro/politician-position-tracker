from datetime import datetime

from pydantic import BaseModel


# --- Source ---
class SourceBase(BaseModel):
    source_type: str = "analysis"  # "post" or "analysis"
    title: str
    url: str
    description: str | None = None


class SourceCreate(SourceBase):
    pass


class SourceOut(SourceBase):
    id: int

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


class StatementCreate(StatementBase):
    politician_id: int
    issue_id: int
    sources: list[SourceCreate] = []


class StatementUpdate(StatementBase):
    politician_id: int
    issue_id: int
    sources: list[SourceCreate] = []


class StatementOut(StatementBase):
    id: int
    politician_id: int
    issue_id: int
    created_at: datetime
    updated_at: datetime
    politician: PoliticianOut
    issue: IssueOut
    sources: list[SourceOut] = []

    model_config = {"from_attributes": True}


class StatementListOut(StatementBase):
    id: int
    politician_id: int
    issue_id: int
    created_at: datetime
    updated_at: datetime
    politician: PoliticianOut
    issue: IssueOut

    model_config = {"from_attributes": True}


# --- Politician detail with statements ---
class PoliticianDetailOut(PoliticianOut):
    statements: list[StatementListOut] = []

    model_config = {"from_attributes": True}


# --- Issue detail with statements ---
class IssueDetailOut(IssueOut):
    statements: list[StatementListOut] = []

    model_config = {"from_attributes": True}
