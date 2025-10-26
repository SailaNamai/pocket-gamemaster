# services.prompt_builder_story_continue.py

import sqlite3
from typing import Tuple
from services.llm_config import GlobalVars
from services.DB_access_pipeline import connect
from services.prompts_kickoffs import Kickoffs
from services.prompt_builder_memory_mid import build_mid_memory
from services.prompt_builder_memory_long import build_long_memory
from services.prompt_builder_indent_helper import indent_one, indent_two, indent_three

LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'story_continue.log'

def get_story_continue_prompts() -> Tuple[str, str]:
    log_path = LOG_DIR / LOG_FILE

    # Start DB data gathering
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Load the base system instruction
        cur.execute("SELECT story_continue FROM system_prompts WHERE id = 1")
        temp = cur.fetchone()
        story_continue = temp[0] if temp and temp[0] is not None else ""

        # Load story parameters
        cur.execute("""
            SELECT
                characters_hardcode,
                prepend_characters,
                characters,
                player_hardcode,
                prepend_player,
                player,
                rules_hardcode,
                prepend_rules,
                rules,
                world_setting_hardcode,
                prepend_world_setting,
                world_setting,
                writing_style_hardcode,
                prepend_writing_style,
                writing_style
            FROM story_parameters
            WHERE id = 1
        """)
        (
          chars_hc, prepend_chars, chars,
          player_hc, prepend_player, player,
          rules_hc, prepend_rules, rules,
          world_hc, prepend_world_setting, world,
          style_hc, prepend_style, style,
        ) = cur.fetchone()

        # Load memories
        cur.execute("SELECT mid_memory_hardcode, long_memory_hardcode FROM memory")
        mid_memory_hc, long_memory_hc = cur.fetchone()
    finally:
        conn.close()

    # Build memories
    mid_memory = build_mid_memory()
    long_memory = build_long_memory()

    number_long = "7. " + long_memory_hc
    ind_long_hc = indent_one(number_long)
    ind_long = indent_three(long_memory)
    ind_mid_hc = indent_one(mid_memory_hc)
    ind_mid = indent_three(mid_memory)

    system_segments = [
        story_continue,
        chars_hc,
        player_hc,
        rules_hc,
        world_hc,
        style_hc,
        style,
        ind_long_hc,
        ind_long,
        ind_mid_hc,
        ind_mid,
    ]
    system_prompt = "\n\n".join(filter(None, system_segments))

    # Load story paragraphs
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, story_id, content, token_cost, outcome
              FROM story_paragraphs
             ORDER BY id
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    # Select recent paragraphs
    max_recent = GlobalVars.tc_budget_recent_paragraphs
    selected, acc = [], 0
    for row in reversed(rows):
        cost = int(row["token_cost"])
        if acc + cost > max_recent:
            break
        selected.append(row)
        acc += cost
    selected.reverse()

    # Identify the last PlayerAction in the selected block
    last_playeraction_index = None
    for idx in range(len(selected) - 1, -1, -1):
        if selected[idx]["story_id"] == "continue_with_UserAction":
            last_playeraction_index = idx
            break

    # Build recent block, inserting outcome only if last PlayerAction
    # is followed by exactly one non-PlayerAction paragraph
    wrapped_texts = []
    for idx, r in enumerate(selected):
        text = r["content"].strip()
        if r["story_id"] == "continue_with_UserAction":
            text = f"<PlayerAction>{text}</PlayerAction>"
            wrapped_texts.append(text)

            if idx == last_playeraction_index and r["outcome"]:
                # Check if exactly one non-player paragraph follows
                if (
                        idx + 1 < len(selected) and
                        selected[idx + 1]["story_id"] != "continue_with_UserAction" and
                        idx + 2 == len(selected)  # ensure it's the last element
                ):
                    outcome_block = indent_one(r["outcome"].strip())
                    wrapped_texts.append(outcome_block)
            continue
        wrapped_texts.append(text)

    indented_wrapped = [indent_one(text) for text in wrapped_texts]
    recent_block = "Here is what happened recently (short term memory):\n\n" + "\n\n".join(indented_wrapped)
    kickoff = Kickoffs.continue_kickoff
    indent_recent = indent_one(recent_block)

    # Collect user segments
    ind_char = indent_one(chars)
    ind_player = indent_one(player)
    ind_rules = indent_one(rules)
    ind_world = indent_one(world)

    user_segments = [
        prepend_chars, ind_char,
        prepend_player, ind_player,
        prepend_rules, ind_rules,
        prepend_world_setting, ind_world,
        indent_recent,
        kickoff,
    ]
    user_prompt = "\n\n".join(filter(None, user_segments))

    # Log both prompts
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_prompt + "\n")

    return system_prompt, user_prompt
