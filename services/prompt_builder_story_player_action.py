# services.prompt_builder_player_action.py

import sqlite3
from typing import Tuple
from services.DB_token_cost import update_story_parameters_cost, update_memory_costs, update_system_prompt_costs
from services.DB_access_pipeline import connect
from services.prompt_builder_indent_helper import indent_one, indent_three
from services.prompt_builder_memory_mid import build_mid_memory
from services.prompt_builder_memory_long import build_long_memory
from services.llm_config import GlobalVars
from services.prompts_kickoffs import Kickoffs

LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'story_player_action.log'

def get_story_player_action_prompts() -> Tuple[str, str]:
    """
    Fetches and concatenates all the story_player_action prompt components from the SQLite database.
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
                     + relevant tagged paragraphs (recent block)
                     + story so far (last n paragraphs within budget)
                     + User attempted action with tag wrap
                     + Outcome (already tag wrapped, appended at end)
    """
    log_path = LOG_DIR / LOG_FILE

    # Update token costs in DB
    update_story_parameters_cost()
    update_memory_costs()
    update_system_prompt_costs()

    # Start DB data gathering
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Load the base system instruction
        cur.execute("""
                SELECT story_player_action
                FROM system_prompts
                WHERE id = 1
            """)
        temp = cur.fetchone()
        story_player_action = temp[0] if temp and temp[0] is not None else ""

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

    finally:
        conn.close()

    # Use helper to dynamically build mid/long-memory based on current memory conveyer belt
    mid_memory = build_mid_memory()
    long_memory = build_long_memory()

    # indent and number for structure
    num_long_hc = "7. " + long_memory_hc
    ind_long_hc = indent_one(num_long_hc)
    ind_long = indent_three(long_memory)
    ind_mid_hc = indent_one(mid_memory_hc)
    ind_mid = indent_three(mid_memory)

    # Assemble system prompt in logical order
    system_segments = [
        story_player_action,
        chars_hc,
        player_hc,
        rules_hc,
        world_hc,
        style_hc,
        # user writing style as system
        style,
        # memories
        ind_long_hc,
        ind_long,
        ind_mid_hc,
        ind_mid,
    ]
    system_prompt = "\n\n".join(filter(None, system_segments))

    # Load all story_paragraphs, ordered by id
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
                    SELECT id, story_id, content, token_cost, outcome, outcome_token_cost
                      FROM story_paragraphs
                     ORDER BY id
                """)
        rows = cur.fetchall()
    finally:
        conn.close()

    # Prepare recent block with budget
    max_recent = GlobalVars.tc_budget_recent_paragraphs
    selected = []
    acc = 0

    # Deduct outcome cost first (if present on the latest row)
    latest_outcome = None
    if rows:
        last_row = rows[-1]
        if last_row["outcome"]:
            latest_outcome = last_row["outcome"].strip()
            outcome_cost = int(last_row["outcome_token_cost"] or 0)
            max_recent -= outcome_cost
            if max_recent < 0:
                max_recent = 0

    # iterate from newest to oldest for story paragraphs
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

    indented_wrapped = [indent_one(text) for text in wrapped_texts]

    recent_block = (
            "Here is what happened recently (short term memory):\n\n"
            + "\n\n".join(indented_wrapped)
    )

    # Append outcome if available
    if latest_outcome:
        recent_block += "\n\n" + latest_outcome

    # indent user values for structure
    ind_chars = indent_one(chars)
    ind_player = indent_one(player)
    ind_rules = indent_one(rules)
    ind_world = indent_one(world)

    # kickoff
    kickoff = Kickoffs.action_kickoff

    # Collect all user-defined segments
    user_segments = [
        prepend_chars, ind_chars,
        prepend_player, ind_player,
        prepend_rules, ind_rules,
        prepend_world_setting, ind_world,
        recent_block, kickoff
    ]

    user_prompt = "\n\n".join(filter(None, user_segments))

    # Log both prompts
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_prompt + "\n")

    return system_prompt, user_prompt