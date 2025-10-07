# services.summarize_mid_memory.py

import subprocess
import sys
import sqlite3

from services.llm_config import Config, GlobalVars
from services.DB_access_pipeline import write_connection, connect
from services.prompt_builder_summarize_mid import get_summarize_mid_memory_prompt
from services.DB_token_cost import count_tokens

LLAMA_CLI_PATH = Config.LLAMA_CLI

def summarize_mid_memory():
    # build prompts
    system_prompt, user_prompt = get_summarize_mid_memory_prompt()

    # invoke llama-cli
    cmd = [
        LLAMA_CLI_PATH,
        "-m", str(Config.MODEL_PATH),
        "--ctx-size", str(Config.N_CTX),
        "--threads", str(Config.N_THREADS),
        "--gpu-layers", str(Config.N_GPU_LAYERS),
        "--temp", str(Config.TEMPERATURE_SUM_LONG),
        "--top-p", str(Config.TOP_P),
        "--repeat-penalty", str(Config.REPEAT_PENALTY),
        "--frequency-penalty", str(Config.FREQUENCY_PENALTY),
        "--presence-penalty", str(Config.PRESENCE_PENALTY),
        "--chat-template-file", str(Config.TEMPLATE_PATH),
        "--system-prompt", system_prompt,
        "--prompt", user_prompt
    ]
    try:
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] llama-cli exited with {e.returncode}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)

    full_out = result.stdout or ""
    print("=== raw stdout ===\n", full_out)

    # isolate assistant response
    marker = f"{user_prompt}assistant"
    assistant_out = full_out.split(marker, 1)[1] if marker in full_out else full_out
    response = assistant_out.split("> EOF by user", 1)[0].strip()

    # count tokens for the summary text
    token_cost = count_tokens(response)

    # persist: update story_paragraphs.summary and summary_token_cost
    with write_connection() as conn:
        conn.row_factory = sqlite3.Row
        # find oldest out‐of‐window user‐action paragraph
        paragraph_id = _find_paragraph_id()
        print(f"[DEBUG] summarizing paragraph id = {paragraph_id!r}")
        if paragraph_id == 0:
            print("[WARN] no paragraph qualified for mid-memory summarization; skipping DB update")
            return
        # Write to DB
        conn.execute("""
                UPDATE story_paragraphs
                   SET summary = ?,
                       summary_token_cost   = ?
                 WHERE id = ?
            """, (response,str(token_cost), paragraph_id)
        )
    return

def _find_paragraph_id() -> int:
    """
    Returns the id for the next paragraph
    that falls outside the recent (tc_budget_recent_paragraphs) +
    mid-memory (tc_budget_mid_memories) windows and has no summary.
    If no such paragraph exists, returns 0.
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Fetch all paragraphs in reverse chronological order
        cur.execute("""
            SELECT id,
                   token_cost,
                   summary,
                   summary_from_action,
                   summary_token_cost
              FROM story_paragraphs
             ORDER BY id DESC
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    threshold_recent = GlobalVars.tc_budget_recent_paragraphs
    threshold_mid = GlobalVars.tc_budget_mid_memories

    for row in rows:
        # Deduct from the recent-token window
        try:
            threshold_recent -= int(row['token_cost'])
        except (TypeError, ValueError):
            pass

        if threshold_recent > 0:
            continue

        # Deduct from the mid-memory window
        try:
            threshold_mid -= int(row['summary_token_cost'])
        except (TypeError, ValueError):
            pass

        if threshold_mid > 0:
            continue

        # Now beyond both windows: look for a summary-triggering paragraph
        if row['summary_from_action'] and not row['summary']:
            return row['id']

    # No actionable paragraph found
    return 0