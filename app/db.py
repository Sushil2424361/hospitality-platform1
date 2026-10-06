"""Database helpers: open connections and create tables. Plain sqlite3, no ORM."""
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_db_path() -> Path:
    """Return the database path and ensure its folder exists."""
    # Check if a custom path is specified in environment variables (e.g. on Render)
    raw_path = os.environ.get("DATABASE_PATH") or os.environ.get("DB_PATH")
    if raw_path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = BASE_DIR / path
    else:
        # Default to restaurant.db in the project root folder
        path = BASE_DIR / "restaurant.db"

    # Ensure the parent folder exists (e.g. if using a subfolder or /tmp)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# Expose DB_PATH for any modules inspecting the path
DB_PATH = get_db_path()


def get_conn():
    """Open a connection. Rows behave like dictionaries: row["item_name"]."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not exist yet (safe to run every time)."""
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))