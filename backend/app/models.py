from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ParsedSubject(BaseModel):
    base_number: Optional[str] = None   # "0172"
    letter_suffix: Optional[str] = None  # "", "a", "b", "aa", ...
    project_abbr: Optional[str] = None  # "BELLAIRE"
    title: Optional[str] = None         # "Concrete Pour"
    is_numbered: bool = False


class EmailTableRow(BaseModel):
    item_id: str
    change_key: str
    subject: str
    sender_name: str
    sender_email: str
    received_time: datetime
    # Duplicate info
    is_duplicate: bool = False
    duplicate_group_id: Optional[str] = None
    duplicate_action: Optional[str] = None  # "keep" | "delete"
    # Numbering info
    is_numbered: bool = False
    proposed_subject: Optional[str] = None
    chain_base: Optional[str] = None
    chain_reason: Optional[str] = None  # "conversation_match" | "body_match" | "new_chain"
    # User overrides (set by frontend)
    include: bool = True
    override_subject: bool = False
    custom_subject: Optional[str] = None
    override_abbr: bool = False
    custom_abbr: Optional[str] = None


class ProjectEmailData(BaseModel):
    project_number: str
    folder_name: str
    rows: list[EmailTableRow]
    duplicate_count: int
    numbering_count: int
    error: Optional[str] = None


class LoadRequest(BaseModel):
    project_numbers: list[str]
    email_limit: int = 500
    time_window_minutes: int = 5


class ApplyDuplicatesRequest(BaseModel):
    project_number: str
    rows: list[EmailTableRow]


class ApplyNumberingRequest(BaseModel):
    project_number: str
    rows: list[EmailTableRow]


class ApplyResult(BaseModel):
    success: bool
    processed: int
    errors: list[str]
    undo_id: Optional[str] = None


class AuthStatus(BaseModel):
    authenticated: bool
    email: Optional[str] = None
    error: Optional[str] = None
