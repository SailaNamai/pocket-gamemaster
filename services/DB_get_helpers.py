# services.DB_get_helpers.py

import re

from services.DB_access_pipeline import connect

def get_last_action():
    """
    Returns the most recent paragraph for the story
    “Continue_with_UserAction” as a dict with the key ``content``.
    If no rows exist, returns ``None``.
    """
    conn = connect(readonly=True)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT content
              FROM story_paragraphs
             WHERE story_id = "Continue_with_UserAction"
             ORDER BY id DESC
             LIMIT 1
        """)
        row = cur.fetchone()
        if row is None:
            return None

        # ``row`` is a one‑element tuple (content,)
        return {"content": row[0]}
    finally:
        conn.close()


def get_last_outcome():
    """
    Returns the most recent outcome row as a dict with keys: outcome.
    If no rows exist, returns None.
    """
    conn = connect(readonly=True)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT outcome
              FROM story_paragraphs
             ORDER BY id DESC
             LIMIT 1
        """)
        row = cur.fetchone()
        if row is None:
            return None
        # row is a tuple (outcome)
        return {"outcome": row[0]}
    finally:
        conn.close()

def clean_outcome(val: str | None) -> str | None:
    if not val:
        return None
    # Remove <Outcome>...</Outcome> tags (case‑insensitive, multiline)
    cleaned = re.sub(r'</?Outcome>', '', val, flags=re.IGNORECASE)
    # Strip leading/trailing whitespace and empty lines
    cleaned = cleaned.strip()
    return cleaned or None