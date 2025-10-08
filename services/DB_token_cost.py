# services.DB_token_cost.py

import sqlite3
import logging
from llama_cpp import Llama
from services.llm_config import Config, GlobalVars
from services.DB_access_pipeline import write_connection, connect
from typing import Optional

# point at the exact same ggml .bin model you pass to llama-cli
# initialize a real Llama tokenizer instance
llm: Llama = Llama(model_path=str(Config.MODEL_PATH))

def count_tokens(text: Optional[str]) -> int:
    """
    Returns how many tokens llama.cpp would "consume" for `text`.
    """
    if not text:
        return 0

    # Normalise to a str in case callers pass bytes by mistake
    if isinstance(text, bytes):
        b = text
    else:
        b = str(text).encode('utf-8')

    try:
        token_ids = llm.tokenize(b, add_bos=False)
    except Exception:
        # If tokenizer fails for any reason, fall back to conservative estimate 0
        return 0

    return len(token_ids)

def get_prompt_cost():
    """
    Calc combined costs for prompts
    It's not totally 100% - some more tokens get consumed along the way (for kickoffs/structure helpers)
    Should be okay, we add 50.
    """
    system = get_system_token_cost()
    memory = get_memory_token_cost()
    story = get_sp_token_cost()
    total = system + memory + story
    safe_total = total + 50
    return int(safe_total)

def get_memory_token_cost():
    conn = connect(readonly=True)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT token_cost
              FROM memory
             WHERE ID = 1
            """
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        raise ValueError("No memory row with ID = 1")

    raw = row[0]
    return int(raw)

def get_system_token_cost():
    """
    Returns highest of sn (story_new), sc (story_continue) or sp (story_player_action)
    """
    conn = connect(readonly=True)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sp_token_cost, sc_token_cost, sn_token_cost
              FROM system_prompts
             WHERE id = 1
            """
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        raise ValueError("No system_prompts row with id = 1")

    # coerce values to int, treating None or non-int as 0 (adjust as needed)
    costs = []
    for v in row:
        try:
            costs.append(int(v))
        except (TypeError, ValueError):
            costs.append(0)

    return max(costs)

def get_sp_token_cost():
    update_story_parameters_cost()
    conn = connect(readonly=True)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT token_cost
              FROM story_parameters
             WHERE ID = 1
            """
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        raise ValueError("No story_parameters row with ID = 1")

    raw = row[0]
    return int(raw)


def check_long_memories_tc() -> bool:
    """
    Returns True if current token cost for long term memories
    is bigger than GlobalVars.tc_budget_long_memories
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Fetch all paragraphs in reverse chronological order
        cur.execute("""
            SELECT id,
                   summary,
                   summary_token_cost
              FROM story_paragraphs
             ORDER BY id DESC
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    # accumulate token cost only for rows that actually have a summary
    total_cost = 0
    for row in rows:
        if row["summary"]:
            val = row["summary_token_cost"]
            try:
                total_cost += int(val) if val is not None else 0
            except (ValueError, TypeError):
                logging.warning("Invalid summary_token_cost for paragraph id %s: %r", row["id"], val)

    # compare against the budget
    return total_cost > GlobalVars.tc_budget_long_memories

def update_system_prompt_costs():
    """
    Reads from system_prompts (id=1), counts tokens for each, and updates *_token_cost.
    """
    with write_connection() as conn:
        # fetch the static prompts
        row = conn.execute("""
            SELECT story_new,
                   story_continue,
                   story_player_action,
                   story_summarize,
                   mid_memory_summarize,
                   tag_generator,
                   eval_system
              FROM system_prompts
             WHERE id = 1
        """).fetchone()
        if row is None:
            raise RuntimeError("No row found in system_prompts (id=1)")

        # count tokens for each prompt
        costs = [count_tokens(text) for text in row]

        # write them back
        conn.execute("""
            UPDATE system_prompts
               SET sn_token_cost = ?,
                   sc_token_cost = ?,
                   sp_token_cost = ?,
                   ss_token_cost = ?,
                   mm_token_cost = ?,
                   tg_token_cost = ?,
                   es_token_cost = ?
             WHERE id = 1
        """, costs)
    return

def update_story_parameters_cost():
    """
    Reads all hardcode/user fields from story_parameters (id=1),
    sums their token counts, and stores the total in token_cost.
    """
    with write_connection() as conn:
        # fetch all text fields except id and token_cost
        cols = [
            "writing_style_hardcode",   "writing_style",
            "world_setting_hardcode",   "world_setting",
            "rules_hardcode",           "rules",
            "player_hardcode",          "player",
            "characters_hardcode",      "characters"
        ]
        row = conn.execute(
            f"SELECT {','.join(cols)} FROM story_parameters WHERE id = 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("No row found in story_parameters (id=1)")

        # sum token counts across all non-empty fields
        total_cost = sum(count_tokens(text) for text in row if text)

        # update the singleton row
        conn.execute("""
            UPDATE story_parameters
               SET token_cost = ?
             WHERE id = 1
        """, (total_cost,))
    return

def update_memory_costs():
    """
    Reads mid_memory_hardcode, mid_memory, long_memory_hardcode, long_memory
    from the singleton memory row (id=1), sums their token counts, and updates
    token_cost with the total.
    """
    with write_connection() as conn:
        # fetch the memory fields
        cols = [
            "mid_memory_hardcode",
            "long_memory_hardcode",
        ]
        row = conn.execute(
            f"SELECT {', '.join(cols)} FROM memory WHERE id = 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("No row found in memory (id=1)")

        # sum token counts across all non-empty fields
        total_cost = sum(count_tokens(text) for text in row if text)

        # update the singleton row
        conn.execute(
            "UPDATE memory SET token_cost = ? WHERE id = 1",
            (total_cost,),
        )
    return
