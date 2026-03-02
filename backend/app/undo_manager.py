"""
Undo/revert support via JSON log files stored in ~/.fortis_email_tool/undo/.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

UNDO_DIR = Path.home() / ".fortis_email_tool" / "undo"


def _ensure() -> None:
    UNDO_DIR.mkdir(parents=True, exist_ok=True)


def save_duplicate_deletion(project_number: str, deleted: list[dict[str, Any]]) -> str:
    """Persist deletion record. Returns operation_id."""
    _ensure()
    op_id = str(uuid.uuid4())[:8]
    record = {
        "operation_id": op_id,
        "type": "duplicate_deletion",
        "timestamp": datetime.now().isoformat(),
        "project_number": project_number,
        "deleted_emails": deleted,
    }
    (UNDO_DIR / f"undo_{op_id}.json").write_text(json.dumps(record, indent=2, default=str))
    return op_id


def save_numbering_changes(project_number: str, changes: list[dict[str, Any]]) -> str:
    """Persist rename record. Returns operation_id."""
    _ensure()
    op_id = str(uuid.uuid4())[:8]
    record = {
        "operation_id": op_id,
        "type": "numbering",
        "timestamp": datetime.now().isoformat(),
        "project_number": project_number,
        "changes": changes,  # [{item_id, change_key, old_subject, new_subject}]
    }
    (UNDO_DIR / f"undo_{op_id}.json").write_text(json.dumps(record, indent=2, default=str))
    return op_id


def list_operations() -> list[dict]:
    """List all undo operations, newest first."""
    _ensure()
    ops: list[dict] = []
    for f in sorted(UNDO_DIR.glob("undo_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            count = len(data.get("deleted_emails") or data.get("changes") or [])
            ops.append({
                "operation_id": data["operation_id"],
                "type": data["type"],
                "timestamp": data["timestamp"],
                "project_number": data["project_number"],
                "count": count,
            })
        except Exception:
            continue
    return ops


def load_record(operation_id: str) -> Optional[dict]:
    path = UNDO_DIR / f"undo_{operation_id}.json"
    return json.loads(path.read_text()) if path.exists() else None
