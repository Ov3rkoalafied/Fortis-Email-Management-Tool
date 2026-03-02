"""
FastAPI application - Fortis Email Management Tool backend.
Serves on http://localhost:8000
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .auth import (
    clear_auth,
    get_cached_token,
    get_user_email,
    interactive_login,
    require_auth,
    verify_domain,
)
from .duplicate_detector import detect_duplicates
from .email_numbering import (
    assign_chains,
    build_chain_metadata,
    derive_folder_abbr,
    get_highest_base,
    parse_subject,
)
from .ews_client import (
    body_hash,
    fetch_bodies,
    fetch_emails_minimal,
    find_project_folders,
    get_account,
)
from .models import (
    ApplyDuplicatesRequest,
    ApplyNumberingRequest,
    ApplyResult,
    AuthStatus,
    EmailTableRow,
    LoadRequest,
    ProjectEmailData,
)
from .undo_manager import (
    list_operations,
    load_record,
    save_duplicate_deletion,
    save_numbering_changes,
)

app = FastAPI(title="Fortis Email Management Tool", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth routes ──────────────────────────────────────────────────────────────

@app.get("/api/auth/status", response_model=AuthStatus)
async def auth_status():
    token = get_cached_token()
    if not token:
        return AuthStatus(authenticated=False)
    email = get_user_email(token)
    if not verify_domain(email):
        return AuthStatus(authenticated=False, error=f"{email} is not a @fortisstructural.com account")
    return AuthStatus(authenticated=True, email=email)


@app.post("/api/auth/login", response_model=AuthStatus)
async def auth_login():
    """Opens browser for interactive OAuth2 login. Blocks until user completes login."""
    try:
        result = await interactive_login()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc

    email = get_user_email(result)
    if not verify_domain(email):
        raise HTTPException(403, f"{email} is not authorized (must be @fortisstructural.com)")
    return AuthStatus(authenticated=True, email=email)


@app.post("/api/auth/logout")
async def auth_logout():
    clear_auth()
    return {"success": True}


# ── Connection test ──────────────────────────────────────────────────────────

@app.get("/api/test/connection")
async def test_connection():
    """Quick smoke test: authenticate + list top-level public folder names."""
    user_email, access_token = require_auth()
    loop = asyncio.get_event_loop()

    def _test():
        account = get_account(user_email, access_token)
        all_public = account.public_folders_root / "All Public Folders"
        names = [f.name for f in list(all_public.children)[:10]]
        return {"status": "ok", "user": user_email, "sample_folders": names}

    return await loop.run_in_executor(None, _test)


# ── Email loading ────────────────────────────────────────────────────────────

@app.post("/api/emails/load")
async def load_emails(request: LoadRequest):
    """
    Load, analyse, and return email rows for all requested project folders.
    Steps per folder:
      1. Fetch minimal metadata (subject, sender, received_time, conversation_id)
      2. Identify potential duplicates via subject+time proximity → fetch bodies for those
      3. Run duplicate detection (body hash + time window)
      4. Fetch bodies for unnumbered emails → run chain assignment
      5. Build and return EmailTableRow list
    """
    user_email, access_token = require_auth()
    loop = asyncio.get_event_loop()

    def _load() -> list[dict]:
        account = get_account(user_email, access_token)
        folders = find_project_folders(account, request.project_numbers)
        results: list[dict] = []

        for proj_num in request.project_numbers:
            folder = folders.get(proj_num)
            if not folder:
                results.append(ProjectEmailData(
                    project_number=proj_num,
                    folder_name="",
                    rows=[],
                    duplicate_count=0,
                    numbering_count=0,
                    error=f"No folder found starting with '{proj_num}'",
                ).model_dump())
                continue

            try:
                folder_name = folder.name
                abbr = derive_folder_abbr(folder_name)

                # ① Fetch minimal metadata
                raw = fetch_emails_minimal(folder, request.email_limit)

                # ② Identify candidates for body fetch (potential duplicates)
                dup_candidate_ids = _find_dup_candidates(raw, request.time_window_minutes)
                bodies: dict[str, str] = {}
                if dup_candidate_ids:
                    pairs = [(e["item_id"], e["change_key"]) for e in raw if e["item_id"] in dup_candidate_ids]
                    bodies = fetch_bodies(account, pairs)
                for email in raw:
                    if email["item_id"] in bodies:
                        email["body_hash"] = body_hash(bodies[email["item_id"]])

                # ③ Duplicate detection
                dup_groups, dup_actions = detect_duplicates(raw, request.time_window_minutes)

                # ④ Chain assignment for unnumbered, non-duplicate emails
                numbered = [e for e in raw if parse_subject(e["subject"]).is_numbered]
                chains = build_chain_metadata(numbered)
                highest_base = get_highest_base(chains)

                unnumbered = [
                    e for e in raw
                    if not parse_subject(e["subject"]).is_numbered
                    and dup_actions.get(e["item_id"]) != "delete"
                ]

                # Fetch bodies for unnumbered emails that don't have one yet
                missing_body = [(e["item_id"], e["change_key"]) for e in unnumbered if not e.get("body_hash")]
                if missing_body:
                    more_bodies = fetch_bodies(account, missing_body)
                    for email in unnumbered:
                        if email["item_id"] in more_bodies:
                            email["body_hash"] = body_hash(more_bodies[email["item_id"]])

                unnumbered_sorted = sorted(unnumbered, key=lambda x: x["received_time"])
                chain_assignments = assign_chains(unnumbered_sorted, chains, abbr, highest_base)
                chain_map = {a["item_id"]: a for a in chain_assignments}

                # Build duplicate group lookup
                dup_group_map: dict[str, dict] = {}
                for grp in dup_groups:
                    for eid in grp["emails"]:
                        dup_group_map[eid] = grp

                # ⑤ Assemble table rows
                rows: list[EmailTableRow] = []
                for email in raw:
                    eid = email["item_id"]
                    parsed = parse_subject(email["subject"])
                    dup_action = dup_actions.get(eid)
                    dup_grp = dup_group_map.get(eid)
                    chain = chain_map.get(eid)

                    row = EmailTableRow(
                        item_id=eid,
                        change_key=email["change_key"],
                        subject=email["subject"],
                        sender_name=email["sender_name"],
                        sender_email=email["sender_email"],
                        received_time=email["received_time"],
                        is_duplicate=dup_action is not None,
                        duplicate_group_id=dup_grp["group_id"] if dup_grp else None,
                        duplicate_action=dup_action,
                        is_numbered=parsed.is_numbered,
                        proposed_subject=chain["proposed_subject"] if chain else None,
                        chain_base=chain["base_number"] if chain else None,
                        chain_reason=chain["reason"] if chain else None,
                        # Default: exclude duplicates marked for deletion
                        include=dup_action != "delete",
                    )
                    rows.append(row)

                results.append(ProjectEmailData(
                    project_number=proj_num,
                    folder_name=folder_name,
                    rows=rows,
                    duplicate_count=sum(1 for r in rows if r.duplicate_action == "delete"),
                    numbering_count=sum(1 for r in rows if r.proposed_subject),
                ).model_dump())

            except Exception as exc:
                results.append(ProjectEmailData(
                    project_number=proj_num,
                    folder_name=getattr(folder, "name", ""),
                    rows=[],
                    duplicate_count=0,
                    numbering_count=0,
                    error=str(exc),
                ).model_dump())

        return results

    return await loop.run_in_executor(None, _load)


def _find_dup_candidates(emails: list[dict], time_window_minutes: int) -> set[str]:
    """
    Quick pre-filter: find emails that share a subject and are close in time.
    We only fetch bodies for these, avoiding unnecessary EWS calls.
    """
    from collections import defaultdict
    subject_groups: dict[str, list[dict]] = defaultdict(list)
    for email in emails:
        subject_groups[email["subject"].lower().strip()].append(email)

    candidate_ids: set[str] = set()
    window_secs = time_window_minutes * 60

    for group in subject_groups.values():
        if len(group) < 2:
            continue
        group_sorted = sorted(group, key=lambda x: x["received_time"])
        for i, e in enumerate(group_sorted):
            for other in group_sorted[i + 1:]:
                diff = abs((other["received_time"] - e["received_time"]).total_seconds())
                if diff <= window_secs:
                    candidate_ids.add(e["item_id"])
                    candidate_ids.add(other["item_id"])
                    break

    return candidate_ids


# ── Apply operations ─────────────────────────────────────────────────────────

@app.post("/api/apply/duplicates", response_model=ApplyResult)
async def apply_duplicates(request: ApplyDuplicatesRequest):
    """Move emails marked for deletion to Deleted Items."""
    user_email, access_token = require_auth()
    loop = asyncio.get_event_loop()

    def _apply():
        account = get_account(user_email, access_token)
        to_delete = [r for r in request.rows if r.include and r.duplicate_action == "delete"]
        deleted_records: list[dict] = []
        errors: list[str] = []

        for row in to_delete:
            try:
                items = list(account.fetch(
                    ids=[(row.item_id, row.change_key)],
                    only_fields=["id", "change_key", "subject"],
                ))
                for item in items:
                    item.soft_delete()
                    deleted_records.append({
                        "item_id": row.item_id,
                        "subject": row.subject,
                        "received_time": str(row.received_time),
                        "sender_email": row.sender_email,
                    })
            except Exception as exc:
                errors.append(f"Failed to delete '{row.subject[:60]}': {exc}")

        undo_id = save_duplicate_deletion(request.project_number, deleted_records) if deleted_records else None
        return ApplyResult(success=not errors, processed=len(deleted_records), errors=errors, undo_id=undo_id)

    result = await loop.run_in_executor(None, _apply)
    return result


@app.post("/api/apply/numbering", response_model=ApplyResult)
async def apply_numbering(request: ApplyNumberingRequest):
    """Rename email subjects according to proposed (or custom) numbering."""
    user_email, access_token = require_auth()
    loop = asyncio.get_event_loop()

    def _apply():
        account = get_account(user_email, access_token)
        to_rename = [
            r for r in request.rows
            if r.include and r.proposed_subject and not r.is_numbered
            and r.duplicate_action != "delete"
        ]
        changes: list[dict] = []
        errors: list[str] = []

        for row in to_rename:
            new_subject = row.custom_subject if row.override_subject else row.proposed_subject
            if not new_subject:
                continue
            try:
                items = list(account.fetch(
                    ids=[(row.item_id, row.change_key)],
                    only_fields=["id", "change_key", "subject"],
                ))
                for item in items:
                    old_subject = item.subject
                    item.subject = new_subject
                    item.save(update_fields=["subject"])
                    changes.append({
                        "item_id": row.item_id,
                        "change_key": row.change_key,
                        "old_subject": old_subject,
                        "new_subject": new_subject,
                    })
            except Exception as exc:
                errors.append(f"Failed to rename '{row.subject[:60]}': {exc}")

        undo_id = save_numbering_changes(request.project_number, changes) if changes else None
        return ApplyResult(success=not errors, processed=len(changes), errors=errors, undo_id=undo_id)

    result = await loop.run_in_executor(None, _apply)
    return result


# ── Undo ─────────────────────────────────────────────────────────────────────

@app.get("/api/undo/history")
async def undo_history():
    require_auth()
    return list_operations()


@app.post("/api/undo/{operation_id}", response_model=ApplyResult)
async def undo_operation(operation_id: str):
    user_email, access_token = require_auth()
    record = load_record(operation_id)
    if not record:
        raise HTTPException(404, f"Undo record '{operation_id}' not found")

    loop = asyncio.get_event_loop()

    def _undo():
        account = get_account(user_email, access_token)
        errors: list[str] = []
        processed = 0

        if record["type"] == "numbering":
            for change in record["changes"]:
                try:
                    items = list(account.fetch(
                        ids=[(change["item_id"],)],
                        only_fields=["id", "change_key", "subject"],
                    ))
                    for item in items:
                        item.subject = change["old_subject"]
                        item.save(update_fields=["subject"])
                        processed += 1
                except Exception as exc:
                    errors.append(str(exc))

        elif record["type"] == "duplicate_deletion":
            errors.append(
                "Deleted emails have been moved to Deleted Items in Outlook. "
                "You can restore them manually from there."
            )

        return ApplyResult(success=not errors, processed=processed, errors=errors)

    return await loop.run_in_executor(None, _undo)
