# services.prompt_builder_tag_recent.py

import sqlite3
from typing import Tuple

from services.DB_access_pipeline import connect
from services.llm_config import GlobalVars
from services.prompt_builder_indent_helper import indent_two, indent_three
from services.prompts_kickoffs import Kickoffs

LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'tag_recent_prompt.log'

def get_prompts_tag_recent() -> Tuple[str, str]:
    """
    Build (system_prompt, user_prompt) for the newest paragraphs.
    - Always include the 3 most recent paragraphs in the user prompt.
    - Then accumulate earlier paragraphs until budget/new, and place that
      accumulated context into the system prompt.
    """
    log_path = LOG_DIR / LOG_FILE

    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # load base system prompt
        cur.execute("SELECT tag_generator FROM system_prompts WHERE id = 1")
        row = cur.fetchone()
        system_tag_generator = row['tag_generator'] if row else ""

        # load tagging_hardcode
        cur.execute("SELECT tagging_hardcode FROM mid_memory_bucket WHERE id = 1")
        bucket = cur.fetchone()
        hardcode_tag_generator = bucket['tagging_hardcode'] if bucket else ""

        # load all paragraphs (newest → oldest)
        cur.execute("""
            SELECT id,
                   story_id,
                   content,
                   token_cost
              FROM story_paragraphs
             ORDER BY id DESC
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    # --- user prompt: 3 newest ---
    user_parts = []
    total_cost = 0
    base_rows = rows[:3]

    for row in base_rows:
        content = row["content"]
        if not content:
            continue
        if row["story_id"] == "continue_with_UserAction":
            user_parts.append(f"<PlayerAction>{content}</PlayerAction>")
        else:
            user_parts.append(content)

        try:
            total_cost += int(row["token_cost"] or 0)
        except (TypeError, ValueError):
            pass

    user_prompt = "\n\n".join(user_parts)
    kickoff = Kickoffs.tag_recent_kickoff
    user_kickoff = kickoff + "\n\n" + user_prompt

    # --- system context: accumulate earlier rows until budget/new ---
    context_parts = []
    for row in rows[3:]:
        story_id = row["story_id"]

        if story_id == "new":
            break

        try:
            cost = int(row["token_cost"] or 0)
        except (TypeError, ValueError):
            cost = 0

        if total_cost + cost > GlobalVars.tc_budget_long_tag:
            break
        total_cost += cost

        content = row["content"]
        if not content:
            continue
        if story_id == "continue_with_UserAction":
            context_parts.append(f"<PlayerAction>{content}</PlayerAction>")
        else:
            context_parts.append(content)

    context_text = "\n\n".join(reversed(context_parts))  # chronological order
    content_headline = "3. **Additional context**:\n\n"
    ind_headline = indent_two(content_headline)
    ind_context = indent_three(context_text)

    # --- assemble system prompt ---
    system_parts = [
        system_tag_generator,
        hardcode_tag_generator,
        ind_headline, ind_context
    ]
    system_prompt = "\n\n".join(p for p in system_parts if p)

    # --- log ---
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_kickoff + "\n")

    return system_prompt, user_kickoff
