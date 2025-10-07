# services.prompt_builder_tag_recent.py

import sqlite3
from typing import Tuple

from services.DB_access_pipeline import connect
from services.llm_config import GlobalVars

LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'tag_recent.log'

def get_prompts_tag_recent() -> Tuple[str, str]:
    """
    Build (system_prompt, user_prompt) for the newest (highest id) paragraphs.
    Paragraphs with story_id = 'continue_with_UserAction' are wrapped in <PlayerAction> tags.
    """
    log_path = LOG_DIR / LOG_FILE

    # open DB
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # load base system prompt
        cur.execute("""
                        SELECT tag_generator
                          FROM system_prompts
                         WHERE id = 1
                    """)
        row = cur.fetchone()
        system_tag_generator = row['tag_generator']

        # load tagging_hardcode from singleton bucket
        cur.execute("""
                        SELECT tagging_hardcode
                          FROM mid_memory_bucket
                         WHERE id = 1
                    """)
        bucket = cur.fetchone()
        hardcode_tag_generator = bucket['tagging_hardcode']

        # load n paragraphs (oldest → newest)
        cur.execute("""
                    SELECT id,
                           story_id,
                           content,
                           summary_from_action,
                           tags_recent
                      FROM story_paragraphs
                     ORDER BY id DESC
                     LIMIT 3
                """)
        rows = cur.fetchall()
    finally:
        conn.close()

    # assemble system prompt
    system_parts = [
        system_tag_generator,
        hardcode_tag_generator
    ]
    system_prompt = "\n\n".join(p for p in system_parts if p)

    # assemble user prompt (3 story_paragraph.content values)
    user_parts = []
    for row in rows:
        content = row["content"]
        if not content:
            continue
        if row["story_id"] == "continue_with_UserAction":
            user_parts.append(f"<PlayerAction>{content}</PlayerAction>")
        else:
            user_parts.append(content)

    user_prompt = "\n\n".join(user_parts)

    # log prompts for debugging
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_prompt + "\n")

    return system_prompt, user_prompt
