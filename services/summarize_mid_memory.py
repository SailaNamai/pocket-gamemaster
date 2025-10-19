# services.summarize_mid_memory.py

import subprocess
import sys
import sqlite3

from services.llm_config import Config, GlobalVars
from services.llm_config_helper import output_cleaner
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
            encoding='utf-8',
            errors='replace',
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] llama-cli exited with {e.returncode}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)

    full_out = result.stdout or ""
    print("=== raw stdout ===\n", full_out)
    generated = output_cleaner(full_out, user_prompt)

    # count tokens for the summary text
    token_cost = count_tokens(generated)

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
            """, (generated,str(token_cost), paragraph_id)
        )
    return

def _find_paragraph_id() -> int:
    """
    1. If any paragraph within the recent or mid-memory windows already has a summary,
       return 0 immediately.
    2. Otherwise, find the first actionable paragraph (summary_from_action present, summary missing)
       that lies beyond both windows.
    3. Collect up to 5 consecutive actionable paragraphs starting from that one
       (ordered oldest to newest).
    4. Return the highest id from that cluster (so the DB update attaches to the newest).
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

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

    # Pass 1: check for summaries inside windows
    for row in rows:
        try:
            threshold_recent -= int(row['token_cost'])
        except (TypeError, ValueError):
            pass
        if threshold_recent > 0:
            if row['summary']:
                return 0
            continue

        try:
            threshold_mid -= int(row['summary_token_cost'])
        except (TypeError, ValueError):
            pass
        if threshold_mid > 0:
            if row['summary']:
                return 0
            continue

        break  # beyond both windows

    # Reset thresholds for actionable search
    threshold_recent = GlobalVars.tc_budget_recent_paragraphs
    threshold_mid = GlobalVars.tc_budget_mid_memories

    actionable_id = None
    for row in rows:
        try:
            threshold_recent -= int(row['token_cost'])
        except (TypeError, ValueError):
            pass
        if threshold_recent > 0:
            continue

        try:
            threshold_mid -= int(row['summary_token_cost'])
        except (TypeError, ValueError):
            pass
        if threshold_mid > 0:
            continue

        if row['summary_from_action'] and not row['summary']:
            actionable_id = row['id']
            break

    if not actionable_id:
        return 0

    # Collect cluster: up to 5 actionable rows with id >= actionable_id
    candidates = [
        r for r in rows
        if r['id'] >= actionable_id and r['summary_from_action'] and not r['summary']
    ]
    candidates_sorted = sorted(candidates, key=lambda r: r['id'])[:5]

    if not candidates_sorted:
        return 0

    # Return the highest id in the cluster
    return max(r['id'] for r in candidates_sorted)
