# services.DB_access_pipeline.py

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
#from services.llm_config import GlobalVars

BASE = Path(__file__).resolve().parent.parent
DB_PATH = "pgm_memory.db"
SCHEMA = BASE / "schema.sql"
#DB_PATH = GlobalVars.DB
_write_lock = threading.Lock()

def connect(readonly=False):
    uri = f"file:{DB_PATH}?mode=rw"
    if not readonly:
        uri = f"file:{DB_PATH}?mode=rwc"
    conn = sqlite3.connect(uri, uri=True, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def write_connection(timeout=15):
    acquired = _write_lock.acquire(timeout=timeout)
    if not acquired:
        raise TimeoutError("Could not acquire DB write lock within timeout")
    try:
        conn = connect(readonly=False)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    finally:
        _write_lock.release()

"""
Examples
with write_connection() as conn:

conn = connect(readonly=True)
    try:
        cursor = conn.cursor()
        cursor.execute(""+1
                SELECT summary,
                       summary_token_cost,
                       tags
                  FROM story_paragraphs
                 ORDER BY id DESC
            ""+1)
        rows = cursor.fetchall()
    finally:
        conn.close()

"""
