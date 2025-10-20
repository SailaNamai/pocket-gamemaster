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
    summarize_ids = _check_long_memories()
    if summarize_ids: summarize_mid_memory(summarize_ids)
    if debug: print("finished summarize mid" if summarize_ids else "skipped summarize mid")

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

def _check_long_memories() -> list[int]:
    """
    Walks through the recent‑token and mid‑memory windows.
    - Returns early (empty list) if any paragraph inside the windows already has a `summary`.
    - After the windows, scans backward until reaching id == 1 or a paragraph with a `summary`.
    - From that point, gathers the 5 lowest‑id paragraphs that have
      `summary_from_action` but no `summary`.
    - Returns the list of those IDs (empty if no candidates).
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id,
                   token_cost,
                   summary,
                   summary_from_action,
                   summary_token_cost
              FROM story_paragraphs
             ORDER BY id DESC
            """
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    # recent‑token window
    recent_budget = GlobalVars.tc_budget_recent_paragraphs
    for row in rows:
        try:
            recent_budget -= int(row["token_cost"])
        except (TypeError, ValueError):
            pass

        if recent_budget > 0:
            # Inside recent window – abort early if a summary already exists
            if row["summary"]:
                return []          # early exit: nothing to do
            continue

        # Exited recent window – stop this pass
        break

    # Pass through the mid‑memory window
    mid_budget = GlobalVars.tc_budget_mid_memories
    for row in rows:
        try:
            mid_budget -= int(row["summary_token_cost"])
        except (TypeError, ValueError):
            pass

        if mid_budget > 0:
            # Inside mid‑memory window – abort early if a summary already exists
            if row["summary"]:
                return []          # early exit: nothing to do
            continue

        # Exited mid‑memory window – stop this pass
        break

    # Scan backwards to the stopping point (id == 1 or a summary)
    candidate_ids: list[int] = []
    for row in rows:
        # Stop condition
        if row["id"] == 1 or row["summary"]:
            # We've reached the boundary – stop scanning further
            break

        # Collect rows that have a summary_from_action but lack a summary
        if row["summary_from_action"] and not row["summary"]:
            candidate_ids.append(int(row["id"]))

    # Return the five lowest IDs (i.e., earliest paragraphs)
    candidate_ids.sort()  # lowest IDs first
    if len(candidate_ids) < 5:
        return []  # not a full cluster → skip
    return candidate_ids[:5]  # exactly five IDs

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


