# services/story_new.py

import subprocess
import sys
import re

from services.llm_config import Config
from services.llm_config_helper import output_cleaner
from services.DB_access_pipeline import write_connection
from services.prompt_builder_story_new import get_story_new_prompts
from services.DB_scrub_story import clear_story_tables
from services.DB_token_cost import count_tokens

LLAMA_CLI_PATH = Config.LLAMA_CLI

def generate_story_new():
    try:
        # Scrub existing story tables for a fresh start
        clear_story_tables()

        # Build prompts
        system_prompt, user_prompt = get_story_new_prompts()
        #user_prompt_with_placeholder = f"{user_prompt}"

        # Run llama-cli
        cmd = [
            LLAMA_CLI_PATH,
            "-m", str(Config.MODEL_PATH),
            "--ctx-size", str(Config.N_CTX),
            "--threads", str(Config.N_THREADS),
            "--gpu-layers", str(Config.N_GPU_LAYERS),
            "--temp", str(Config.TEMPERATURE_NEW),
            "--top-p", str(Config.TOP_P),
            "--repeat-penalty", str(Config.REPEAT_PENALTY),
            "--frequency-penalty", str(Config.FREQUENCY_PENALTY),
            "--presence-penalty", str(Config.PRESENCE_PENALTY),
            "--chat-template-file", str(Config.TEMPLATE_PATH),
            "--system-prompt", system_prompt,
            "--prompt", user_prompt,
        ]
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, # raw_bytes = result.stdout ;;; full_out = raw_bytes.decode('utf-8', errors='replace')
            encoding='utf-8',
            errors='replace',
            check=True,
        )
        full_out = result.stdout or ""
        print("=== raw stdout ===\n", full_out)
        generated = output_cleaner(full_out, user_prompt)

        # Collapse newlines and strip whitespace
        generated = re.sub(r"\n+", " ", generated).strip()

        # Count tokens for this new paragraph
        token_cost = count_tokens(generated)

        # Persist into SQLite, including token_cost
        with write_connection() as conn:
            # find next paragraph_index
            cur = conn.execute(
                "SELECT COALESCE(MAX(paragraph_index), 0) + 1 "
                "FROM story_paragraphs WHERE story_id = ?",
                ("new",),
            )
            next_index = cur.fetchone()[0]

            # INSERT and get last row id
            insert_cur = conn.execute(
                """
                INSERT INTO story_paragraphs
                  (story_id, paragraph_index, content, token_cost)
                VALUES (?, ?, ?, ?)
                """,
                ("new", next_index, generated, token_cost),
            )
            paragraph_id = insert_cur.lastrowid

        # Return id & content
        return {"id": paragraph_id, "content": generated}

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] llama-cli exited with code {e.returncode}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)

    except Exception as e:
        print("--- Story_new error ---")
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
