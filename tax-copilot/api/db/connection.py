"""Per-call SQLite connection helper (suitable for use as a FastAPI Depends)."""

import os
import sqlite3

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DB_PATH = os.path.join(DB_DIR, "tax_copilot.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    # check_same_thread=False: FastAPI dispatches the sync `get_db` generator
    # dependency and the sync route body to its threadpool as separate
    # submissions, with no guarantee they land on the same worker thread --
    # this connection is still only ever used by one request at a time, just
    # not necessarily from a single OS thread, so disabling sqlite3's default
    # same-thread check is the correct fix, not a race-safety issue.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Creates tables from schema.sql if missing. Idempotent (CREATE TABLE IF NOT EXISTS)."""
    conn = get_connection()
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()
