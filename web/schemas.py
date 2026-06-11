from pydantic import BaseModel, Field


class PasswordRequest(BaseModel):
    password: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


class EntryCreate(BaseModel):
    title: str = Field(min_length=1)
    username: str = ""
    password: str = Field(min_length=1)
    url: str = ""
    notes: str = ""


class EntryUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    url: str | None = None
    notes: str | None = None


class GenerateRequest(BaseModel):
    length: int = Field(default=16, ge=1)
    symbols: bool = True
    digits: bool = True
    title: str = ""


class EntrySummary(BaseModel):
    id: str
    title: str
    username: str
    url: str
    updated_at: str


class EntryDetail(EntrySummary):
    password: str
    notes: str
    created_at: str


class StatusResponse(BaseModel):
    vault_exists: bool
    logged_in: bool
    entry_count: int | None = None
    session_age_seconds: int | None = None
    session_timeout_seconds: int | None = None
    csrf_token: str | None = None
    username: str | None = None


class AuthResponse(BaseModel):
    csrf_token: str
    username: str


class GenerateResponse(BaseModel):
    password: str
    saved: bool = False
    title: str | None = None
