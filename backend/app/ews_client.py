"""
EWS client wrapping exchangelib.

Key design: fetch only the fields we need per operation.
- Initial email scan: id, change_key, subject, sender, datetime_received, conversation_id
- Body fetch (only for potential duplicates + unnumbered): text_body
This is significantly faster than COM which always loads all properties.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Optional

from exchangelib import Account, Configuration, DELEGATE
from exchangelib.credentials import OAuth2AuthorizationCodeCredentials
from exchangelib.items import Message

from .auth import CLIENT_ID, TENANT_ID

EXCHANGE_SERVER = "outlook.office365.com"
WHITESPACE_RE = re.compile(r"[\s\u200a\u200c\ufeff]+")


def _make_credentials(access_token: str) -> OAuth2AuthorizationCodeCredentials:
    return OAuth2AuthorizationCodeCredentials(
        client_id=CLIENT_ID,
        client_secret=None,
        tenant_id=TENANT_ID,
        access_token={"token_type": "Bearer", "access_token": access_token},
    )


def get_account(user_email: str, access_token: str) -> Account:
    """
    Create (or recreate) an exchangelib Account for the given user.
    We recreate on each call so a fresh token is always used.
    Lightweight - no network call at construction time.
    """
    credentials = _make_credentials(access_token)
    config = Configuration(server=EXCHANGE_SERVER, credentials=credentials)
    return Account(
        primary_smtp_address=user_email,
        config=config,
        autodiscover=False,
        access_type=DELEGATE,
    )


def find_project_folders(account: Account, project_numbers: list[str]) -> dict[str, object]:
    """
    Walk All Public Folders and return {project_number: folder} for each match.
    A folder matches if its name starts with the 5-digit project number.
    """
    try:
        all_public = account.public_folders_root / "All Public Folders"
    except Exception as exc:
        raise RuntimeError(f"Cannot access Public Folders: {exc}") from exc

    results: dict[str, object] = {}
    remaining = set(project_numbers)

    for folder in all_public.children:
        if not remaining:
            break
        for proj in list(remaining):
            if folder.name.startswith(proj):
                results[proj] = folder
                remaining.discard(proj)
                break

    return results


def fetch_emails_minimal(folder, limit: int) -> list[dict]:
    """
    Fetch emails with only the fields needed for initial analysis.
    Returns a list of plain dicts (JSON-serializable).
    """
    records: list[dict] = []
    try:
        qs = (
            folder.all()
            .only("id", "change_key", "subject", "sender", "datetime_received", "conversation_id")
            .order_by("-datetime_received")[:limit]
        )
        for item in qs:
            if not isinstance(item, Message):
                continue
            sender_email = ""
            sender_name = ""
            if item.sender:
                sender_email = item.sender.email_address or ""
                sender_name = item.sender.name or ""
            conv_id = None
            if item.conversation_id:
                # ConversationId object has an .id attribute
                conv_id = getattr(item.conversation_id, "id", str(item.conversation_id))
            records.append({
                "item_id": item.id,
                "change_key": item.change_key,
                "subject": item.subject or "(no subject)",
                "sender_email": sender_email,
                "sender_name": sender_name,
                "received_time": item.datetime_received,
                "conversation_id": conv_id,
                "body_hash": None,
            })
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch emails: {exc}") from exc

    return records


def fetch_bodies(account: Account, id_ck_pairs: list[tuple[str, str]]) -> dict[str, str]:
    """
    Batch-fetch plain text bodies for the given (item_id, change_key) pairs.
    Returns {item_id: raw_body_text}.
    """
    if not id_ck_pairs:
        return {}
    results: dict[str, str] = {}
    try:
        items = list(account.fetch(ids=id_ck_pairs, only_fields=["id", "change_key", "text_body", "body"]))
        for item in items:
            body = getattr(item, "text_body", None)
            if not body:
                raw = getattr(item, "body", None)
                body = str(raw) if raw else ""
            results[item.id] = body
    except Exception as exc:
        # Fallback: return empty strings so processing can continue
        for item_id, _ in id_ck_pairs:
            results.setdefault(item_id, "")
        print(f"Warning: body fetch failed: {exc}")
    return results


# ── Body normalisation ──────────────────────────────────────────────────────

_REPLY_SEPARATORS = ["\nFrom:", "\nSent:", "\n________________________________", "\n--", "\n> "]


def _extract_latest_reply(body: str) -> str:
    idxs = [body.find(s) for s in _REPLY_SEPARATORS if body.find(s) != -1]
    return body[: min(idxs)] if idxs else body


def normalize_body(body: str) -> str:
    body = _extract_latest_reply(body)
    body = unicodedata.normalize("NFC", body)
    body = WHITESPACE_RE.sub("", body)
    return body.lower()


def body_hash(raw_body: str) -> str:
    return hashlib.sha256(normalize_body(raw_body).encode("utf-8")).hexdigest()
