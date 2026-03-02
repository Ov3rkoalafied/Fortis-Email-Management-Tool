"""
Email numbering and chain management.

Numbering standard: NNNN[letters] - PROJECT ABBR - Email Title
  Examples: 0104 - BELLAIRE - Concrete Pour
            0104a - BELLAIRE - Concrete Pour
            0104b - BELLAIRE - Concrete Pour
            0105 - BELLAIRE - New Subject

Chain assignment priority (for unnumbered emails):
  1. Conversation ID match against existing chain
  2. Body hash match against chain's sample bodies
  3. Create new chain (next sequential base number)
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Optional

from .models import ParsedSubject

# Matches: 0104a - BELLAIRE - Concrete Pour
_NUMBERED_RE = re.compile(
    r"^(\d{4})([a-z]*)\s*-\s*([^-]+?)\s*-\s*(.+)$",
    re.IGNORECASE,
)
_RE_FW_RE = re.compile(r"^(RE:|FW:|FWD:)\s*", re.IGNORECASE)

# How many body hashes / entry IDs to keep per chain for matching
_MAX_BODIES_PER_CHAIN = 25
_MAX_IDS_PER_CHAIN = 8


def parse_subject(subject: str) -> ParsedSubject:
    m = _NUMBERED_RE.match((subject or "").strip())
    if m:
        return ParsedSubject(
            base_number=m.group(1),
            letter_suffix=m.group(2).lower(),
            project_abbr=m.group(3).strip(),
            title=m.group(4).strip(),
            is_numbered=True,
        )
    return ParsedSubject(is_numbered=False)


# ── Letter suffix arithmetic ────────────────────────────────────────────────

def _letter_sort_key(letter: Optional[str]) -> tuple:
    """None (no email yet) < "" (first email) < "a" < "b" < ... < "z" < "aa" ..."""
    if letter is None:
        return (-1, "")
    return (len(letter), letter)


def _next_letter(current_max: Optional[str]) -> str:
    """
    None  → ""   (first email in chain – no letter)
    ""    → "a"  (second email)
    "a"   → "b", ..., "z" → "aa", "aa" → "ab", ...
    """
    if current_max is None:
        return ""
    if current_max == "":
        return "a"
    chars = list(current_max)
    i = len(chars) - 1
    while i >= 0:
        if chars[i] < "z":
            chars[i] = chr(ord(chars[i]) + 1)
            return "".join(chars)
        chars[i] = "a"
        i -= 1
    return "a" + "".join(chars)


# ── Chain metadata ──────────────────────────────────────────────────────────

def build_chain_metadata(numbered_emails: list[dict[str, Any]]) -> dict[str, dict]:
    """
    Scan already-numbered emails and build chain metadata.
    Returns {base_number: {abbr, letter_max, canonical_title, conv_ids, body_hashes, entry_ids}}
    """
    chains: dict[str, dict] = {}

    for email in numbered_emails:
        parsed = parse_subject(email["subject"])
        if not parsed.is_numbered or not parsed.base_number:
            continue

        base = parsed.base_number
        if base not in chains:
            chains[base] = {
                "abbr": parsed.project_abbr,
                "letter_max": parsed.letter_suffix,
                "title_counter": Counter({parsed.title: 1}),
                "canonical_title": parsed.title,
                "conv_ids": set(),
                "body_hashes": [],
                "entry_ids": [],
            }
        else:
            info = chains[base]
            # Update letter_max
            if _letter_sort_key(parsed.letter_suffix) > _letter_sort_key(info["letter_max"]):
                info["letter_max"] = parsed.letter_suffix
            info["title_counter"][parsed.title] += 1
            info["canonical_title"] = info["title_counter"].most_common(1)[0][0]

        info = chains[base]
        if email.get("conversation_id"):
            info["conv_ids"].add(email["conversation_id"])
        if email.get("body_hash") and len(info["body_hashes"]) < _MAX_BODIES_PER_CHAIN:
            info["body_hashes"].append(email["body_hash"])
        if len(info["entry_ids"]) < _MAX_IDS_PER_CHAIN:
            info["entry_ids"].append(email["item_id"])

    return chains


def get_highest_base(chains: dict[str, dict]) -> int:
    if not chains:
        return 0
    try:
        return max(int(b) for b in chains if b.isdigit())
    except ValueError:
        return 0


# ── Chain assignment ────────────────────────────────────────────────────────

def assign_chains(
    unnumbered_emails: list[dict[str, Any]],
    chains: dict[str, dict],
    folder_abbr: str,
    highest_base: int,
) -> list[dict]:
    """
    Assign each unnumbered email to an existing chain or create a new one.
    unnumbered_emails must be sorted oldest-first so letter suffixes are in order.
    Returns list of assignment dicts.
    """
    assignments: list[dict] = []
    next_base = highest_base + 1
    # Working copy so we can mutate letter_max as we assign
    working_chains: dict[str, dict] = {k: dict(v) for k, v in chains.items()}
    # Track chains created this session
    new_chains: dict[str, dict] = {}

    for email in unnumbered_emails:
        assignment = _assign_one(email, working_chains, folder_abbr, next_base)
        assignments.append(assignment)

        base = assignment["base_number"]
        if base not in working_chains:
            working_chains[base] = {
                "abbr": assignment["project_abbr"],
                "letter_max": assignment["letter_suffix"],
                "title_counter": Counter({assignment["title"]: 1}),
                "canonical_title": assignment["title"],
                "conv_ids": {email["conversation_id"]} if email.get("conversation_id") else set(),
                "body_hashes": [email["body_hash"]] if email.get("body_hash") else [],
                "entry_ids": [email["item_id"]],
            }
            new_chains[base] = working_chains[base]
            if int(base) >= next_base:
                next_base = int(base) + 1
        else:
            working_chains[base]["letter_max"] = assignment["letter_suffix"]
            if email.get("conversation_id"):
                working_chains[base]["conv_ids"].add(email["conversation_id"])
            if email.get("body_hash"):
                hashes = working_chains[base]["body_hashes"]
                if len(hashes) < _MAX_BODIES_PER_CHAIN:
                    hashes.append(email["body_hash"])

    return assignments


def _assign_one(
    email: dict,
    chains: dict[str, dict],
    folder_abbr: str,
    next_base: int,
) -> dict:
    conv_id = email.get("conversation_id")
    bh = email.get("body_hash")

    # 1. Conversation ID match
    if conv_id:
        for base, info in chains.items():
            if conv_id in info.get("conv_ids", set()):
                return _make_assignment(email, base, info, "conversation_match", True)

    # 2. Body hash match
    if bh:
        for base, info in chains.items():
            if bh in info.get("body_hashes", []):
                return _make_assignment(email, base, info, "body_match", True)

    # 3. New chain
    base_str = str(next_base).zfill(4)
    title = _RE_FW_RE.sub("", email.get("subject", "")).strip() or "Untitled"
    return {
        "item_id": email["item_id"],
        "base_number": base_str,
        "letter_suffix": "",
        "project_abbr": folder_abbr,
        "title": title,
        "proposed_subject": f"{base_str} - {folder_abbr} - {title}",
        "reason": "new_chain",
        "chain_was_existing": False,
    }


def _make_assignment(
    email: dict, base: str, chain_info: dict, reason: str, existing: bool
) -> dict:
    new_letter = _next_letter(chain_info.get("letter_max"))
    abbr = chain_info.get("abbr") or ""
    title = chain_info.get("canonical_title") or _RE_FW_RE.sub("", email.get("subject", "")).strip()
    proposed = f"{base}{new_letter} - {abbr} - {title}"
    return {
        "item_id": email["item_id"],
        "base_number": base,
        "letter_suffix": new_letter,
        "project_abbr": abbr,
        "title": title,
        "proposed_subject": proposed,
        "reason": reason,
        "chain_was_existing": existing,
    }


def derive_folder_abbr(folder_name: str) -> str:
    """Derive a short project abbreviation from the folder name."""
    # Strip leading 5-digit project number
    name = re.sub(r"^\d+\s*", "", folder_name).strip()
    if not name:
        return "PROJ"
    words = name.split()
    if len(words) == 1:
        return words[0][:8].upper()
    return "".join(w[0] for w in words[:5]).upper()
