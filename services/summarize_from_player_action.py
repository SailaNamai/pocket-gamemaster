# services.summarize_from_player_action.py

import subprocess
import sys
import sqlite3
from services.llm_config import Config
from services.llm_config_helper import output_cleaner
from services.prompt_builder_summarize_from_player_action import (
    get_summarize_from_player_action_prompts
)
from services.DB_token_cost import count_tokens
from services.DB_access_pipeline import write_connection

LLAMA_CLI_PATH = Config.LLAMA_CLI

def summarize_from_player_action():
    # build prompts
    system_prompt, user_prompt, write_id = get_summarize_from_player_action_prompts()

    # invoke llama-cli
    cmd = [
        LLAMA_CLI_PATH,
        "-m", str(Config.MODEL_PATH),
        "--ctx-size", str(Config.N_CTX),
        "--threads", str(Config.N_THREADS),
        "--gpu-layers", str(Config.N_GPU_LAYERS),
        "--temp", str(Config.TEMPERATURE_SUM_MID),
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

    summary_text = generated.strip()

    # count tokens for the summary text
    token_cost = count_tokens(summary_text)

    # persist: update story_paragraphs.summary_from_action, cost
    with write_connection() as conn:

        paragraph_id = write_id

        # single UPDATE
        conn.execute("""
            UPDATE story_paragraphs
               SET summary_from_action = ?,
                   summary_token_cost   = ?
             WHERE id = ?
        """, (
            summary_text,
            str(token_cost),
            paragraph_id,
        ))