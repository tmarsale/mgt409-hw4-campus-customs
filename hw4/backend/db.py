"""Database location and connections.

Set CAMPUS_CUSTOMS_DB to point the backend at a copy of the database (used by tests).
Everything opens the database read-only except account registration.
"""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

HW4_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = HW4_DIR / "data"
DB_PATH = Path(os.environ.get("CAMPUS_CUSTOMS_DB", DATA_DIR / "campus_customs.db")).resolve()


@contextmanager
def connect(*, write: bool = False) -> Iterator[sqlite3.Connection]:
    """Open the database for one request: read-only unless write=True."""
    conn = sqlite3.connect(DB_PATH) if write else sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
