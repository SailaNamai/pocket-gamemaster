# services.prompt_builder_story_continue.py

import sqlite3
from typing import Tuple
from services.llm_config import GlobalVars
from services.DB_access_pipeline import connect
from services.prompt_builder_memory_mid import build_mid_memory
from services.prompt_builder_memory_long import build_long_memory

LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'story_continue.log'

def get_story_continue_prompts() -> Tuple[str, str]:
    """
    Fetches and concatenates all the story_continue prompt components from the SQLite database.
    Returns:
      system_prompt: string combining:
                     system prompt
                     + all hardcode story parameters
                     + writing_style (user)
                     + long-term memories
                     + mid-term memories
      user_prompt:   string combining:
                     prepend + dynamic characters, player, rules,
                     world setting, and writing style if needed
                     + relevant tagged paragraphs # tagging not yet implemented
                     + story so far (last n paragraphs)
    """
    log_path = LOG_DIR / LOG_FILE

    # Start DB data gathering
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Load the base system instruction
        cur.execute("""
            SELECT story_continue
            FROM system_prompts
            WHERE id = 1
        """)
        temp = cur.fetchone()
        story_continue = temp[0] if temp and temp[0] is not None else ""

        # Load story parameters: hardcodes, prepends, user values
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
        cur.execute("""
            SELECT
                mid_memory_hardcode,
                long_memory_hardcode
            FROM memory
        """)
        mid_memory_hc, long_memory_hc = cur.fetchone()

        # Load tagged paragraphs
        # tagging not yet implemented
    finally:
        conn.close()

    # Use helper to dynamically build mid/long-memory based on current memory conveyor belt
    mid_memory = build_mid_memory()
    long_memory = build_long_memory()

    # Assemble system prompt in logical order
    system_segments = [
        story_continue.strip(),
        chars_hc.strip(),
        player_hc.strip(),
        rules_hc.strip(),
        world_hc.strip(),
        style_hc.strip(),
        # user writing as style as system
        style.strip(),
        # memories
        long_memory_hc.strip(),
        long_memory.strip(),
        mid_memory_hc.strip(),
        mid_memory.strip(),
    ]
    system_prompt = "\n\n".join(filter(None, system_segments))

    """
    Assemble user_segments including:
      - all custom inputs (player, rules, world, etc.)
      - a “recent_block” that fills up to GlobalVars.tc_budget_recent_paragraphs
    """

    # Load all story_paragraphs, ordered by paragraph_index
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
                SELECT id, story_id, content, token_cost
                  FROM story_paragraphs
                 ORDER BY id
            """)
        rows = cur.fetchall()
    finally:
        conn.close()

    # Pick as many of the newest paragraphs as will fit under the ceiling
    max_recent = GlobalVars.tc_budget_recent_paragraphs
    selected = []
    acc = 0

    # iterate from newest to oldest
    for row in reversed(rows):
        cost = int(row["token_cost"])
        if acc + cost > max_recent:
            break
        selected.append(row)
        acc += cost

    # restore original chronological order
    selected.reverse()

    # Build the “recent_block” with UserAction wrapping
    wrapped_texts = []
    for r in selected:
        text = r["content"].strip()
        if r["story_id"] == "continue_with_UserAction":
            text = f"<PlayerAction>{text}</PlayerAction>"
        wrapped_texts.append(text)

    recent_block = (
            "Here is what happened in the last paragraphs:\n\n"
            + "\n\n".join(wrapped_texts)
    )
    # Collect all user-defined segments
    user_segments = [prepend_chars.strip(), chars.strip(), prepend_player.strip(), player.strip(),
                     prepend_rules.strip(), rules.strip(), prepend_world_setting.strip(), world.strip(), recent_block]

    user_prompt = "\n\n".join(filter(None, user_segments))

    # Log both prompts
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_prompt + "\n")

    return system_prompt, user_prompt