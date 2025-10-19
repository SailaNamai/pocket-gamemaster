# services.prompt_builder_story_new.py

from typing import Tuple
from services.llm_config import GlobalVars
from services.DB_token_cost import update_story_parameters_cost
from services.DB_access_pipeline import connect
from services.prompt_builder_indent_helper import indent_one, indent_three
from services.prompts_kickoffs import Kickoffs
from services.prompt_builder_memory_long import build_long_memory
from services.prompt_builder_memory_mid import build_mid_memory

LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'story_new.log'

def get_story_new_prompts() -> Tuple[str, str]:
    """
    Fetches and concatenates all the story_new prompt components from the SQLite database.
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
    """
    log_path = LOG_DIR / LOG_FILE

    # Start DB action
    conn = connect(readonly=True)
    try:
        cur = conn.cursor()

        # Load the base system instruction
        cur.execute("SELECT story_new FROM system_prompts WHERE id = 1")
        (story_new,) = cur.fetchone()

        # Load story parameters: hardcodes, prepends, and user values
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
          world_hc, prepend_world, world,
          style_hc, prepend_style, style
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

    mid_memory = build_mid_memory()
    long_memory = build_long_memory()

    # indent and number to fit the structure
    number_long = "7. " + long_memory_hc
    ind_long_hc = indent_one(number_long)
    ind_long = indent_three(long_memory)
    ind_mid_hc = indent_one(mid_memory_hc)
    ind_mid = indent_three(mid_memory)

    # Assemble system prompt in logical order
    system_segments = [
        story_new,
        chars_hc,
        player_hc,
        rules_hc,
        world_hc,
        style_hc,
        # user writing as style as system
        style,
        # memories
        ind_long_hc,
        ind_long,
        ind_mid_hc,
        ind_mid,
    ]

    system_prompt = "\n\n".join(filter(None, system_segments))

    # indent user values
    ind_chars = indent_one(chars)
    ind_player = indent_one(player)
    ind_rules = indent_one(rules)
    ind_world = indent_one(world)

    # Assemble user prompt
    user_segments = [
        prepend_chars,
        ind_chars,
        prepend_player,
        ind_player,
        prepend_rules,
        ind_rules,
        prepend_world,
        ind_world,
        # prepend_style,
        # style,
    ]

    user_prompt = "\n\n".join(filter(None, user_segments))
    kickoff = Kickoffs.new_kickoff
    user_kickoff = user_prompt + kickoff

    # Log both prompts
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_kickoff + "\n")

    update_story_parameters_cost()
    return system_prompt, user_kickoff