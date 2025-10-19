# services.prompt_builder_summarize_mid.py

import sqlite3
from typing import Tuple
from services.llm_config import GlobalVars
from services.DB_access_pipeline import connect
from services.prompts_kickoffs import Kickoffs

LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'summarize_mid_memory.log'

def get_summarize_mid_memory_prompt() -> Tuple[str, str]:
    """
    Fetches and concatenates all the summarize mid-term memory prompt components from the SQLite database.
    Returns:
      system_prompt: string of:
                     system prompt
      user_prompt:   string of:
                     paragraph to summarize wrapped in <Summary>...</Summary>
    """
    log_path = LOG_DIR / LOG_FILE

    # Start DB data gathering
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Load the base system instruction
        cur.execute("""
                SELECT mid_memory_summarize
                FROM system_prompts
                WHERE id = 1
            """)
        temp = cur.fetchone()
        mid_memory_summarize = temp[0] if temp and temp[0] is not None else ""
    finally:
        conn.close()

    # Build system prompt
    # might attach more later, depends on how it goes
    system_prompt = mid_memory_summarize

    # Build user prompt, wrap in <Summary> tag
    user_prompt = f"<Summary>{_find_paragraph_to_summarize()}</Summary>"
    kickoff = Kickoffs.long_memory_kickoff
    user_kickoff = user_prompt + kickoff

    # Log both prompts
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_kickoff + "\n")

    return system_prompt, user_kickoff

def _find_paragraph_to_summarize() -> str:
    """
    1. If any paragraph within the recent or mid-memory windows already has a summary,
       return "" immediately.
    2. Otherwise, find the first actionable paragraph (summary_from_action present, summary missing)
       that lies beyond both windows.
    3. Collect up to 5 consecutive summary_from_action entries starting from that paragraph
       (ordered oldest to newest) and return them joined with newlines.
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Fetch all paragraphs in reverse chronological order (newest first)
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

    # Pass 1: Walk through windows and check for any summaries
    for row in rows:
        try:
            threshold_recent -= int(row['token_cost'])
        except (TypeError, ValueError):
            pass
        if threshold_recent > 0:
            if row['summary']:
                return ""  # summary already present in recent window
            continue

        try:
            threshold_mid -= int(row['summary_token_cost'])
        except (TypeError, ValueError):
            pass
        if threshold_mid > 0:
            if row['summary']:
                return ""  # summary already present in mid-memory window
            continue

        # Once beyond both windows, stop checking for summaries
        break

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
        return ""

    # Collect up to 5 summary_from_action entries with higher id (newer rows)
    candidates = [
        r for r in rows
        if r['id'] >= actionable_id and r['summary_from_action'] and not r['summary']
    ]

    # Sort ascending by id (oldest → newest) and take up to 5
    candidates_sorted = sorted(candidates, key=lambda r: r['id'])[:5]

    return "\n".join(r['summary_from_action'] for r in candidates_sorted)
