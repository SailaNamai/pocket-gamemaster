# services.prompt_builder_tag_long.py

import sqlite3
from typing import Tuple

from services.llm_config import GlobalVars
from services.DB_access_pipeline import connect
from services.prompts_kickoffs import Kickoffs
from services.prompt_builder_indent_helper import indent_one, indent_two, indent_three

LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'tagging_system.log'

def get_tagging_system_prompts(id_to_tag: int) -> Tuple[str, str]:
    """
    Build (system_prompt, user_prompt, write_id) for the given id_to_tag.

    Behavior:
        - Walk backwards from id_to_tag (DESC).
        - Collect paragraphs with story_id in {continue_with_UserAction, continue_without_UserAction}.
        - Stop when tc_budget_long_tag is exceeded or story_id='new'.
        - Wrap continue_with_UserAction in <PlayerAction>…</PlayerAction>.
    Structure:
        - System prompt: tag_generator_system_prompt + get_tagging_style + collected context.
        - User prompt: kickoff + <Summary>…</Summary> of id_to_tag.
    """
    log_path = LOG_DIR / LOG_FILE

    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1) load base system prompt
        cur.execute("SELECT tag_generator FROM system_prompts WHERE id = 1")
        row = cur.fetchone()
        system_tag_generator = row['tag_generator'] if row and row['tag_generator'] else ''

        # 2) load tagging style
        cur.execute("SELECT tagging_hardcode FROM mid_memory_bucket WHERE id = 1")
        bucket = cur.fetchone()
        tagging_style = bucket['tagging_hardcode'] if bucket and bucket['tagging_hardcode'] else ''

        # 3) load all paragraphs (newest → oldest for backwards walk)
        cur.execute("""
            SELECT id,
                   story_id,
                   content,
                   token_cost,
                   summary
              FROM story_paragraphs
             ORDER BY id DESC
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    # 4) walk backwards from id_to_tag
    excerpt = []
    total_cost = 0
    started = False

    for row in rows:
        rid = int(row['id'])
        if rid == id_to_tag:
            started = True  # mark starting point
        if not started:
            continue  # skip until we reach the starting id

        story_id = row['story_id']

        # stop if we hit a "new" boundary
        if story_id == 'new':
            break

        # stop if budget exceeded
        try:
            cost = int(row['token_cost'])
        except (TypeError, ValueError):
            cost = 0
        if total_cost + cost > GlobalVars.tc_budget_long_tag:
            break
        total_cost += cost

        # only include relevant story_ids
        if story_id in ('continue_with_UserAction', 'continue_without_UserAction'):
            text = row['content']
            if story_id == 'continue_with_UserAction':
                text = f"\n<PlayerAction>{text}</PlayerAction>\n"
            excerpt.append(text)

    # reverse so earliest → latest
    context_text = "\n".join(reversed(excerpt))  # reverse back to chronological

    # add headline and indent for structure
    headline = "3. **Additional context**:\n"
    ind_headline = indent_two(headline)
    ind_text = indent_three(context_text)

    # 5) system prompt
    system_parts = [
        system_tag_generator,
        tagging_style,
        ind_headline, ind_text
    ]
    system_prompt = "\n\n".join(p for p in system_parts if p)

    # 6) user prompt: kickoff + summary of id_to_tag
    kickoff = Kickoffs.tag_long_kickoff
    target_summary = None
    for row in rows:
        if int(row['id']) == id_to_tag:
            target_summary = row['summary']
            break
    summary_wrapped = f"<Summary>{target_summary}</Summary>" if target_summary else ""
    user_prompt = f"{kickoff}\n\n{summary_wrapped}"

    # 7) log
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_prompt + "\n\n")
        log_f.write(f"=== WRITE_ID ===\n{id_to_tag}\n")

    return system_prompt, user_prompt

