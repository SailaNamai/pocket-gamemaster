# services/prompt_builder_eval_action.py

import sqlite3
from typing import Tuple
from services.DB_token_cost import update_story_parameters_cost, update_system_prompt_costs, count_tokens
from services.DB_access_pipeline import connect
from services.prompt_builder_memory_mid import build_mid_memory
from services.prompt_builder_memory_long import build_long_memory
from services.llm_config import GlobalVars, Config

LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'evaluate_action.log'

def get_eval_player_action_prompts() -> Tuple[str, str]:
    """
    Build the system and user prompts for evaluating a player action.
    See docstring spec for details.
    """
    log_path = LOG_DIR / LOG_FILE

    # Update token costs in DB (still useful for other parts of pipeline)
    update_story_parameters_cost()
    update_system_prompt_costs()

    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # --- Load system prompt base ---
        cur.execute("SELECT eval_system FROM system_prompts WHERE id = 1")
        row = cur.fetchone()
        eval_system = row["eval_system"] if row else ""

        # --- Load action eval bucket ---
        cur.execute("SELECT eval_sheet, easy, medium, hard, difficulty FROM action_eval_bucket WHERE id = 1")
        row = cur.fetchone()
        eval_sheet, easy, medium, hard, difficulty = row if row else ("", "", "", "", "medium")

        if difficulty.lower() == "easy":
            ruleset = easy
        elif difficulty.lower() == "hard":
            ruleset = hard
        else:
            ruleset = medium

        # --- Load story parameters ---
        cur.execute("""
            SELECT writing_style_hardcode, writing_style,
                   world_setting_hardcode, world_setting,
                   rules_hardcode, rules,
                   prepend_player, player,
                   prepend_characters, characters
            FROM story_parameters
            WHERE id = 1
        """)
        (
            style_hc, style,
            world_hc, world,
            rules_hc, rules,
            prepend_player, player,
            prepend_chars, chars
        ) = cur.fetchone()

        # --- Load memories (hardcodes only) ---
        cur.execute("SELECT mid_memory_hardcode, long_memory_hardcode FROM memory")
        mid_memory_hc, long_memory_hc = cur.fetchone()

        # --- Load story paragraphs ---
        cur.execute("SELECT id, story_id, content FROM story_paragraphs ORDER BY id DESC LIMIT 1")
        rows = cur.fetchall()
    finally:
        conn.close()

    # Build dynamic memories
    mid_memory = build_mid_memory()
    long_memory = build_long_memory()

    # System prompt assembly
    system_segments = [
        eval_system.strip(),
        ruleset.strip(),
        eval_sheet.strip(),
        world_hc.strip(), world.strip(),
        rules_hc.strip(), rules.strip(),
        prepend_chars.strip(), chars.strip(),
        prepend_player.strip(), player.strip(),
        long_memory_hc.strip(), long_memory.strip(),
        mid_memory_hc.strip(), mid_memory.strip()
    ]
    system_prompt = "\n\n".join(filter(None, system_segments))

    # User prompt assembly
    # kickoff
    kickoff = "Attempted action to evaluate:"

    # most recent paragraph (highest id)
    recent_para = rows[0] if rows else None
    action_text = f"<Evaluate>{recent_para['content'].strip()}</Evaluate>"

    user_prompt = "\n\n".join([kickoff, action_text])

    # We can only now choose memories, because token cost was undetermined before:
    combined_prompt = f"{system_prompt}\n\n{user_prompt}"
    tc = count_tokens(combined_prompt)

    # Append system prompt with recent memories (respect token budget)
    recent_memories = _choose_memories(tc)
    system_prompt = f"{system_prompt}\n\n{recent_memories}" if recent_memories else system_prompt

    # Log both prompts
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_prompt + "\n")

    return system_prompt, user_prompt

def _choose_memories(tc: int) -> str:
    """
    Selects recent paragraphs (excluding the very latest, which is already in user_prompt)
    until we hit the available token budget.
    Wraps paragraphs with story_id == 'continue_with_PlayerAction' in <PreviousAction> tags.
    """
    budget = Config.N_CTX
    remaining = budget - tc

    if remaining > GlobalVars.tc_budget_recent_paragraphs:
        remaining = GlobalVars.tc_budget_recent_paragraphs

    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # find the highest id
        cur.execute("SELECT MAX(id) as max_id FROM story_paragraphs")
        max_id = cur.fetchone()["max_id"]
        if not max_id:
            return ""

        # fetch paragraphs below the highest id, newest first
        cur.execute(
            "SELECT id, story_id, content, token_cost FROM story_paragraphs "
            "WHERE id < ? ORDER BY id DESC",
            (max_id,)
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    selected = []
    acc = 0
    for row in rows:
        cost = int(row["token_cost"])
        if acc + cost > remaining:
            break
        selected.append(row)
        acc += cost

    selected.reverse()

    if not selected:
        return ""

    texts = []
    for r in selected:
        text = r["content"].strip()
        if r["story_id"] == "continue_with_PlayerAction":
            text = f"<PreviousAction>{text}</PreviousAction>"
        texts.append(text)

    return "Here is what happened most recently:\n\n" + "\n\n".join(texts)