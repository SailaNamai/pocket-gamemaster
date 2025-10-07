# services.prompt_builder_tagging_system

import os
import sqlite3
from typing import Tuple, Optional

from services.llm_config import GlobalVars
from services.DB_access_pipeline import connect

LOG_DIR  = 'logs'
LOG_FILE = 'tagging_system.log'

def get_tagging_system_prompts() -> Tuple[str, str, Optional[int]]:
    """
    Build (system_prompt, user_prompt, write_id) for the first
    out-of-window 'continue_with_UserAction' without a tag.

    New behavior:
    - If the initial player action is followed by a non-player paragraph
      and then another player action (pattern: action, non-action, action),
      keep scanning past that second action.
    - Tag every included player-action paragraph with <PlayerAction>...</PlayerAction>.
    - Return write_id which is the highest paragraph id of a player action
      included in the final excerpt, or None when no excerpt is selected.
    """
    # ensure logging directory
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, LOG_FILE)

    # open DB
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1) load base system prompt (tag generator)
        cur.execute("""
                SELECT tag_generator
                  FROM system_prompts
                 WHERE id = 1
            """)
        row = cur.fetchone()
        system_tag_generator = row['tag_generator'] if row and row['tag_generator'] else ''

        # 2) load tagging_hardcode from singleton bucket
        cur.execute("""
                SELECT tagging_hardcode
                  FROM mid_memory_bucket
                 WHERE id = 1
            """)
        bucket = cur.fetchone()
        hardcode_tag_generator = bucket['tagging_hardcode'] if bucket and bucket['tagging_hardcode'] else ''

        # 3) load all paragraphs (oldest → newest)
        cur.execute("""
                SELECT id,
                       story_id,
                       content,
                       token_cost,
                       summary_from_action,
                       tags
                  FROM story_paragraphs
                 ORDER BY id ASC
            """)
        rows = cur.fetchall()
    finally:
        conn.close()

    # 4) find boundary where recent-token window ends
    threshold = GlobalVars.tc_budget_recent_paragraphs
    boundary_idx = len(rows) - 1
    for idx in range(len(rows) - 1, -1, -1):
        try:
            cost = int(rows[idx]['token_cost'])
        except (TypeError, ValueError):
            cost = 0

        threshold -= cost
        if threshold <= 0:
            boundary_idx = idx
            break

    # 5) locate most recent untagged action up to boundary_idx
    action_idx = None
    for i in range(boundary_idx, -1, -1):
        r = rows[i]
        if r['story_id'] == 'continue_with_UserAction' and not r['tags']:
            action_idx = i
            break

    # 6) slice from that action up to (but not including) the next action,
    #    applying the "keep going" rule described above
    excerpt = []
    write_id = None
    if action_idx is not None:
        end_idx = len(rows) - 1
        for j in range(action_idx + 1, len(rows)):
            if rows[j]['story_id'] == 'continue_with_UserAction':
                # pattern match: action, non-action, action -> skip the immediate second action
                if (j == action_idx + 2) and (rows[action_idx + 1]['story_id'] != 'continue_with_UserAction'):
                    # skip this action and continue searching for a later action
                    continue
                end_idx = j - 1
                break

        # collect excerpt, tag every player-action, track highest player-action id (write_id)
        max_action_id = None
        for k in range(action_idx, end_idx + 1):
            row = rows[k]
            text = row['content']
            if row['story_id'] == 'continue_with_UserAction':
                text = f"<PlayerAction>{text}</PlayerAction>"
                try:
                    pid = int(row['id'])
                except (TypeError, ValueError):
                    pid = None
                if pid is not None:
                    if max_action_id is None or pid > max_action_id:
                        max_action_id = pid
            excerpt.append(text)

        write_id = max_action_id

    recent_story = "\n".join(excerpt)

    # 7) assemble system prompt
    system_parts = [
        system_tag_generator,
        hardcode_tag_generator
    ]
    system_prompt = "\n\n".join(p for p in system_parts if p)

    # 8) assemble user prompt
    kickoff = "Apply to this story excerpt:"
    user_prompt = f"{kickoff}\n\n{recent_story}" if recent_story else kickoff

    # 9) log prompts for debugging (include write_id)
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_prompt + "\n\n")
        log_f.write(f"=== WRITE_ID ===\n{write_id}\n")

    return system_prompt, user_prompt, write_id
