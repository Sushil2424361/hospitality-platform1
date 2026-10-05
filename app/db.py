"""Database helpers: open connections and create tables. Plain sqlite3, no ORM."""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "restaurant.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_conn():
    """Open a connection. Rows behave like dictionaries: row["item_name"]."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not exist yet (safe to run every time)."""
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))