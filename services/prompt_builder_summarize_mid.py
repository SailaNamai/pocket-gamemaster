# services/prompt_builder_summarize_mid.py
import sqlite3
from typing import Tuple, List
from services.llm_config import GlobalVars
from services.DB_access_pipeline import connect
from services.prompts_kickoffs import Kickoffs

LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'summarize_mid_memory.log'


def get_summarize_mid_memory_prompt(summarize_ids: List[int]) -> Tuple[str, str]:
    """
    Build the prompts for a mid‑memory summarization request.

    Parameters
    ----------
    summarize_ids: List[int]
        IDs (≤5) returned by `_check_long_memories`.  If the list is empty,
        the function returns empty strings – the caller can simply skip the
        LLM call.

    Returns
    -------
    system_prompt: str
        The base system instruction (from `system_prompts.mid_memory_summarize`).

    user_prompt: str
        `<Summary>…</Summary>` containing the concatenated
        `summary_from_action` texts for the supplied IDs, followed by the
        long‑memory kickoff text.
    """
    log_path = LOG_DIR / LOG_FILE

    # ------------------------------------------------------------------
    # 1️⃣  Load the static system prompt from the DB
    # ------------------------------------------------------------------
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT mid_memory_summarize
            FROM system_prompts
            WHERE id = 1
            """
        )
        row = cur.fetchone()
        system_prompt = row["mid_memory_summarize"] if row and row["mid_memory_summarize"] else ""
    finally:
        conn.close()

    # ------------------------------------------------------------------
    # 2️⃣  If there are no IDs to summarise, return empty prompts
    # ------------------------------------------------------------------
    if not summarize_ids:
        return system_prompt, ""

    # ------------------------------------------------------------------
    # 3️⃣  Pull the `summary_from_action` text for each requested ID
    # ------------------------------------------------------------------
    # Preserve the order the caller gave us (normally oldest → newest)
    placeholders = ",".join("?" for _ in summarize_ids)

    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT id, summary_from_action
              FROM story_paragraphs
             WHERE id IN ({placeholders})
            """,
            summarize_ids,
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    # Map id → text for quick lookup (some IDs might be missing – guard against it)
    id_to_text = {int(r["id"]): r["summary_from_action"] or "" for r in rows}

    # Build the concatenated paragraph block in the order supplied
    paragraph_block = "\n".join(id_to_text.get(pid, "") for pid in summarize_ids)

    # ------------------------------------------------------------------
    # 4️⃣  Assemble the user prompt
    # ------------------------------------------------------------------
    user_prompt = f"<Summary>{paragraph_block}</Summary>"
    user_kickoff = user_prompt + Kickoffs.long_memory_kickoff

    # ------------------------------------------------------------------
    # 5️⃣  Log the prompts (useful for debugging)
    # ------------------------------------------------------------------
    with open(log_path, "w", encoding="utf-8") as log_f:
        log_f.write("=== SYSTEM PROMPT ===\n")
        log_f.write(system_prompt + "\n\n")
        log_f.write("=== USER PROMPT ===\n")
        log_f.write(user_kickoff + "\n")

    return system_prompt, user_kickoff
