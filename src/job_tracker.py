"""SQLite-backed job application tracker."""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "job_tracker.db"

STATUSES = [
    "Bookmarked",
    "Applied",
    "Phone Screen",
    "Interview",
    "Technical Assessment",
    "Offer",
    "Rejected",
    "Withdrawn",
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create the applications table if it doesn't exist."""
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Bookmarked',
            url TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            applied_date TEXT DEFAULT '',
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_application(
    company: str,
    title: str,
    status: str = "Bookmarked",
    url: str = "",
    notes: str = "",
    applied_date: str = "",
) -> int:
    """Insert a new application and return its id."""
    conn = _connect()
    cur = conn.execute(
        """INSERT INTO applications (company, title, status, url, notes, applied_date, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (company, title, status, url, notes, applied_date, _now()),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    assert row_id is not None
    return row_id


def update_status(app_id: int, status: str) -> None:
    """Update the status of an application."""
    conn = _connect()
    conn.execute(
        "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
        (status, _now(), app_id),
    )
    conn.commit()
    conn.close()


def update_application(app_id: int, **fields: str) -> None:
    """Update arbitrary fields on an application."""
    allowed = {"company", "title", "status", "url", "notes", "applied_date"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values: list[Any] = [*updates.values(), app_id]
    conn = _connect()
    sql = f"UPDATE applications SET {set_clause} WHERE id = ?"  # noqa: S608  column names come from `allowed`
    conn.execute(sql, values)
    conn.commit()
    conn.close()


def delete_application(app_id: int) -> None:
    """Delete an application by id."""
    conn = _connect()
    conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def get_all_applications() -> list[dict[str, Any]]:
    """Return all applications ordered by most recently updated."""
    conn = _connect()
    rows = conn.execute("SELECT * FROM applications ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def export_csv() -> str:
    """Export all applications to a CSV string."""
    apps = get_all_applications()
    if not apps:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=apps[0].keys())
    writer.writeheader()
    writer.writerows(apps)
    return buf.getvalue()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
