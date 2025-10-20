# services/summarize_mid_memory.py
import subprocess
import sys
import sqlite3
from typing import List

from services.llm_config import Config
from services.llm_config_helper import output_cleaner
from services.DB_access_pipeline import write_connection
from services.prompt_builder_summarize_mid import get_summarize_mid_memory_prompt
from services.DB_token_cost import count_tokens

LLAMA_CLI_PATH = Config.LLAMA_CLI


def summarize_mid_memory(summarize_ids: List[int]) -> None:
    """
    Generate a mid‑memory summary for the paragraph cluster identified by
    `_check_long_memories`.  Only the **highest‑id** paragraph in the cluster
    receives the new summary.
    """
    system_prompt, user_prompt = get_summarize_mid_memory_prompt(summarize_ids)

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
        "--prompt", user_prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] llama-cli exited with {e.returncode}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)

    raw_output = result.stdout or ""
    print("=== raw stdout ===\n", raw_output)

    generated = output_cleaner(raw_output, user_prompt)

    token_cost = count_tokens(generated)

    highest_id = max(summarize_ids)

    with write_connection() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            UPDATE story_paragraphs
               SET summary = ?,
                   summary_token_cost = ?
             WHERE id = ?
            """,
            (generated, str(token_cost), highest_id),
        )
    return
