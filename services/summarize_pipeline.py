# services.summarize_pipeline.py

import sqlite3
from services.llm_config import GlobalVars
from services.summarize_from_player_action import summarize_from_player_action
from services.summarize_mid_memory import summarize_mid_memory
from services.summarize_tag_long import summarize_create_tags
from services.summarize_tag_recent import summarize_tag_recent
from services.DB_access_pipeline import connect
from services.DB_token_cost import check_long_memories_tc

def summarize():
    debug = True

    # Mid-term memory: create summary from player action if needed
    handle = _check_mid_memories()
    if handle: summarize_from_player_action()
    if debug: print("finished summarize from_player_action" if handle else "skipped summarize from_player_action")

    # Long-term memory: create summary if needed
    handle = _check_long_memories()
    if handle: summarize_mid_memory()
    if debug: print("finished summarize mid" if handle else "skipped summarize mid")

    # Missing tags: create tags for a long-term memory if needed
    handle, tag_id = _check_missing_tags()
    if handle: summarize_create_tags(tag_id)
    if debug: print("finished summarize create_tags" if handle else "skipped summarize create_tags")

    # Long-term memory budget check: tag recent story if budget full
    handle = check_long_memories_tc()
    if handle: summarize_tag_recent()
    if debug: print("finished summarize tag_recent" if handle else "skipped summarize tag_recent")

    if debug: print("Backend done.")
    return

def _check_missing_tags():
    """
    Returns (True, highest_id) if there is at least one summary without tags.
    Otherwise, returns (False, None).
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT id,
                   summary,
                   tags
              FROM story_paragraphs
             ORDER BY id DESC
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    missing_ids = []
    for row in rows:
        summary = row["summary"]
        tags = row["tags"]

        if summary and (tags is None or str(tags).strip() == ""):
            missing_ids.append(int(row["id"]))

    if missing_ids:
        return True, max(missing_ids)
    return False, None


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
    Returns True if there is a cluster of new 'summary_from_action' (mid-term memory)
    paragraphs that fall outside the recent (token_cost) + mid-memory (summary_token_cost)
    token windows and have no summary. Otherwise, returns False.
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

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

    # Pass 1: check for summaries inside windows
    for row in rows:
        try:
            threshold_recent -= int(row['token_cost'])
        except (TypeError, ValueError):
            pass
        if threshold_recent > 0:
            if row['summary']:
                return False
            continue

        try:
            threshold_mid -= int(row['summary_token_cost'])
        except (TypeError, ValueError):
            pass
        if threshold_mid > 0:
            if row['summary']:
                return False
            continue

        break  # beyond both windows

    # Reset thresholds for actionable search
    threshold_recent = GlobalVars.tc_budget_recent_paragraphs
    threshold_mid = GlobalVars.tc_budget_mid_memories

    actionable_id = None
    for row in rows:
        try:
            threshold_recent -= int(row['token_cost'])
        except (TypeError, ValueError):
            pass
        if threshold_recent > 0:
            continue

        try:
            threshold_mid -= int(row['summary_token_cost'])
        except (TypeError, ValueError):
            pass
        if threshold_mid > 0:
            continue

        if row['summary_from_action'] and not row['summary']:
            actionable_id = row['id']

    if not actionable_id:
        return False

    # Collect cluster: up to 5 actionable rows with id >= actionable_id
    candidates = [
        r for r in rows
        if r['id'] >= actionable_id and r['summary_from_action'] and not r['summary']
    ]
    candidates_sorted = sorted(candidates, key=lambda r: r['id'])[:5]

    return bool(candidates_sorted)
