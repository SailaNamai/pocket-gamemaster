# services.prompt_builder_summarize_mid.py

import sqlite3
from typing import Tuple
from services.llm_config import GlobalVars
from services.DB_access_pipeline import connect

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

    # Log both prompts
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_prompt + "\n")

    return system_prompt, user_prompt

def _find_paragraph_to_summarize() -> str:
    """
    Returns the summary_from_action text for the next paragraph
    that falls outside the recent (tc_budget_recent_paragraphs) +
    mid-memory (tc_budget_mid_memories) windows and has no summary.
    If no such paragraph exists, returns an empty string.
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Fetch all paragraphs in reverse chronological order
        cur.execute("""
            SELECT token_cost,
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
            threshold_recent -= int(row['token_cost'])
        except (TypeError, ValueError):
            pass

        if threshold_recent > 0:
            continue

        # Deduct from the mid-memory window
        try:
            threshold_mid -= int(row['summary_token_cost'])
        except (TypeError, ValueError):
            pass

        if threshold_mid > 0:
            continue

        # Now beyond both windows: look for a summary-triggering paragraph
        if row['summary_from_action'] and not row['summary']:
            return row['summary_from_action']

    # No actionable paragraph found
    return ""