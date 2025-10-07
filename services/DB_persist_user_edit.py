# services.DB_persist_user_edit.py
"""
selector: #story-history, .mid-synopsis-area, .long-synopsis-area
    for each
        for all paragraphID
            if newText = ""
                where DB story_paragraphs.id = paragraphID
                    empty entire DB row
            else
                where DB story_paragraphs.id = paragraphID
                    overwrite DB story_paragraphs.summary_from_action (mid) or
                    overwrite DB story_paragraphs.summary (long) or
                    overwrite DB story_paragraphs.content (history)
                    finally
                        do count_tokens(newText) and write return into story_paragraphs.summary_token_cost (mid and long)
                        do count_tokens(newText) and write return into story_paragraphs.token_cost (history)
"""

import sqlite3
from services.DB_token_cost import count_tokens
from typing import Any, Dict, List, Union
from services.llm_config import GlobalVars
from services.DB_access_pipeline import write_connection

DB_PATH = GlobalVars.DB

# Column mapping by selector
# selector -> (column_to_write, token_cost_column)
COLUMN_MAP = {
    '#story-history': ('content', 'token_cost'),
    '.mid-synopsis-area': ('summary_from_action', 'summary_token_cost'),
    '.long-synopsis-area': ('summary', 'summary_token_cost'),
}

def _apply_update(cursor: sqlite3.Cursor, paragraph_id: str, col: str, token_col: str, new_text: str) -> None:
    """
    Update a single paragraph row setting col = new_text and token_col = token_count.
    If new_text is None or empty string, treat according to caller (we still write empty string).
    """
    # Compute token cost (guard empty)
    token_count = count_tokens(new_text or "")
    cursor.execute(
        f"UPDATE story_paragraphs SET {col} = ?, {token_col} = ? WHERE id = ?",
        (new_text, token_count, paragraph_id)
    )

def _apply_delete(cursor: sqlite3.Cursor, paragraph_id: str) -> None:
    """
    Mark the paragraph's textual and token columns as NULL while preserving the row.
    """
    cursor.execute("""
      DELETE FROM story_paragraphs
      WHERE id = ?
    """, (paragraph_id,))


def persist_user_edit(user_edits: Union[Dict[str, Any], List[Dict[str, Any]], None]) -> bool:
    """
    Persist candidate-style user edits to the SQLite DB.

    user_edits: either
      - a candidate object: { ts: "...", diffs: [...] }
      - a diffs list: [ { selector, action, paragraphId, storyId, originalText?, newText? }, ... ]
      - None or empty -> nothing to do (returns True)

    Behavior:
      - For each diff:
          * match selector to which DB column to write
          * if action == 'delete' or newText == '' -> clear textual fields for that paragraph (see _apply_delete)
          * if action in ('update', 'insert') -> write newText to the mapped column and update token count
      - All operations are executed inside a transaction. On exception, rollback and return False.
    """
    if not user_edits:
        return True

    if isinstance(user_edits, dict) and 'diffs' in user_edits:
        diffs = user_edits.get('diffs') or []
    elif isinstance(user_edits, list):
        diffs = user_edits
    else:
        print("persist_user_edit: unexpected user_edits shape")
        return False

    if not diffs:
        return True

    try:
        with write_connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            for d in diffs:
                if not isinstance(d, dict):
                    print("persist_user_edit: skipping invalid diff entry:", d)
                    continue

                action = d.get('action')
                selector = d.get('selector')
                paragraph_id = (
                        d.get('paragraphId')
                        or d.get('paragraph_id')
                        or d.get('paragraphID')
                        or d.get('paragraph-id')
                )
                new_text = d.get('newText')

                if not paragraph_id:
                    print("persist_user_edit: skipping diff without paragraphId:", d)
                    continue

                col, token_col = COLUMN_MAP.get(selector, COLUMN_MAP['#story-history'])

                if action == 'delete' or (new_text is not None and str(new_text) == ''):
                    _apply_delete(cur, paragraph_id)
                elif action in ('update', 'insert') or new_text is not None:
                    safe_text = '' if new_text is None else str(new_text)
                    _apply_update(cur, paragraph_id, col, token_col, safe_text)
                else:
                    print("persist_user_edit: skipping unrecognized action:", d)

            # no explicit commit/close needed; write_connection handles it
            return True

    except Exception as exc:
        print("persist_user_edit: exception while persisting edits:", exc)
        return False

