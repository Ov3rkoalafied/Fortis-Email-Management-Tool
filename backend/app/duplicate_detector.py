"""
Duplicate email detection.

Logic (ported from DuplicateEmailDeleter.py):
1. Group emails by normalized body hash.
2. Within each group, use a 5-minute sliding time window.
3. Emails with the same body hash within the window are duplicates.
4. Prefer to keep emails whose subject starts with 4 digits (already numbered).
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import timedelta
from typing import Any


def detect_duplicates(
    emails: list[dict[str, Any]],
    time_window_minutes: int = 5,
) -> tuple[list[dict], dict[str, str]]:
    """
    emails: list of dicts with keys: item_id, subject, received_time, body_hash (may be None)
    Returns:
        duplicate_groups: list of {group_id, emails: [item_id,...], keep_id, reason}
        actions:          {item_id: "keep" | "delete"}
    """
    window_secs = time_window_minutes * 60

    # Only process emails that have a body hash (we skip those without)
    hashed = [e for e in emails if e.get("body_hash")]

    # Group by body_hash
    hash_groups: dict[str, list[dict]] = defaultdict(list)
    for email in hashed:
        hash_groups[email["body_hash"]].append(email)

    groups: list[dict] = []
    actions: dict[str, str] = {}

    for body_hash_val, group in hash_groups.items():
        if len(group) < 2:
            continue

        group.sort(key=lambda x: x["received_time"], reverse=True)
        processed_ids: set[str] = set()

        for i, email in enumerate(group):
            if email["item_id"] in processed_ids:
                continue

            window: list[dict] = [email]
            base_time = email["received_time"]

            for other in group[i + 1:]:
                if other["item_id"] in processed_ids:
                    continue
                diff = abs((other["received_time"] - base_time).total_seconds())
                if diff <= window_secs:
                    window.append(other)

            if len(window) < 2:
                processed_ids.add(email["item_id"])
                continue

            keeper = _choose_keeper(window)
            group_id = str(uuid.uuid4())[:8]

            groups.append({
                "group_id": group_id,
                "emails": [e["item_id"] for e in window],
                "keep_id": keeper["item_id"],
                "reason": "numbered_subject" if _is_numbered(keeper["subject"]) else "first",
            })

            for e in window:
                actions[e["item_id"]] = "keep" if e["item_id"] == keeper["item_id"] else "delete"
                processed_ids.add(e["item_id"])

    return groups, actions


def _choose_keeper(emails: list[dict]) -> dict:
    """Prefer email whose subject begins with 4 digits (already logged/numbered)."""
    for email in emails:
        if _is_numbered(email.get("subject", "")):
            return email
    return emails[0]


def _is_numbered(subject: str) -> bool:
    return len(subject) >= 4 and subject[:4].isdigit()
