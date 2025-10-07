# services.summarize_pipeline.py

import sqlite3
from services.llm_config import GlobalVars
from services.summarize_from_player_action import summarize_from_player_action
from services.summarize_mid_memory import summarize_mid_memory
from services.summarize_tag_mid import summarize_create_tags
from services.summarize_tag_recent import summarize_tag_recent
from services.DB_access_pipeline import connect
from services.DB_token_cost import check_long_memories_tc

def summarize():
    debug = True
    # See if we need to create a mid-term memory
    handle = _check_mid_memories()
    if handle: summarize_from_player_action()
    if handle and debug: print("finished summarize from_player_action")
    if handle: summarize_create_tags()
    if handle and debug: print("finished summarize create_tags")
    # See if we need to create a long-term memory
    handle = _check_long_memories()
    if handle: summarize_mid_memory()
    if handle and debug: print("finished summarize mid")
    # See if our long term memory budget is full
    # (if True we need to tag the most recent story, or we have nothing to compare against)
    handle = check_long_memories_tc()
    if handle: summarize_tag_recent()
    if handle and debug: print("finished summarize tag_recent")
    if debug: print("Backend done.")
    return

def _check_mid_memories() -> bool:
    """
    Returns True if there is a "new" 'continue_with_UserAction' paragraph
    that falls outside the recent-token window and has no summary_from_action,
    and no paragraph with a higher id already has a summary_from_action.
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Fetch all paragraphs in reverse chronological order
        cur.execute("""
            SELECT id,
                   story_id,
                   token_cost,
                   summary_from_action
              FROM story_paragraphs
             ORDER BY id DESC
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    threshold = GlobalVars.tc_budget_recent_paragraphs

    # Precompute a mapping of id -> bool(summary exists) for quick checks
    id_has_summary = {}
    for r in rows:
        try:
            rid = int(r['id'])
        except (TypeError, ValueError):
            continue
        id_has_summary[rid] = bool(r['summary_from_action'])

    for row in rows:
        # Safely cast token_cost to int
        try:
            cost = int(row['token_cost'])
        except (TypeError, ValueError):
            cost = 0

        # Deduct until threshold drops to zero or below
        threshold -= cost
        if threshold > 0:
            # Still within the recent-token window
            continue

        # Once we're out of the window, look for the next UserAction
        if row['story_id'] == "continue_with_UserAction":
            # If that paragraph has never been summarized from action, consider triggering summarization
            try:
                current_id = int(row['id'])
            except (TypeError, ValueError):
                return False

            if id_has_summary.get(current_id, False):
                return False

            # Check that no paragraph with a higher id has a summary_from_action
            # This is a little convoluted, but we need it
            for higher_id, has_summary in id_has_summary.items():
                if higher_id > current_id and has_summary:
                    return False

            return True

    return False

def _check_long_memories() -> bool:
    """
    Returns True if there is a new 'summary_from_action' (mid-term memory) paragraph
    that falls outside the recent (token_cost) + mid-memory (summary_token_cost)
    token window and has no summary. Otherwise, returns False.
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Fetch all paragraphs in reverse chronological order
        cur.execute("""
            SELECT id,
                   token_cost,
                   summary,
                   summary_from_action,
                   summary_token_cost
              FROM story_paragraphs
             ORDER BY id DESC
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    threshold_recent = GlobalVars.tc_budget_recent_paragraphs
    threshold_mid = GlobalVars.tc_budget_mid_memories

    for row in rows:
        # Deduct from the recent-token window
        try:
            recent_cost = int(row['token_cost'])
        except (TypeError, ValueError):
            recent_cost = 0

        threshold_recent -= recent_cost
        if threshold_recent > 0:
            # Still inside the recent window
            continue

        # Deduct from the mid-memory window
        try:
            mid_cost = int(row['summary_token_cost'])
        except (TypeError, ValueError):
            mid_cost = 0

        threshold_mid -= mid_cost
        if threshold_mid > 0:
            # Still inside the mid-memory window
            continue

        # We're now beyond both windows.
        # Look for the next summary_from_action paragraph.
        if not row['summary_from_action']:
            # Not a summary-triggering paragraph: keep scanning
            continue

        # We found a summary_from_action that has no summary yet?
        if not row['summary']:
            return True   # Needs summarizing

        return False      # Already summarized

    return False # No actionable paragraph found