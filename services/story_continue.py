# services.story_continue.py

import subprocess
import sys
import re

from services.llm_config import Config, GlobalVars
from services.prompt_builder_story_continue import get_story_continue_prompts
from services.DB_token_cost import count_tokens
from services.DB_access_pipeline import write_connection

LLAMA_CLI_PATH = Config.LLAMA_CLI
DB_PATH = GlobalVars.DB

def generate_story_continue():
    try:
        # Build prompts
        system_prompt, user_prompt = get_story_continue_prompts()

        # Run llama-cli
        cmd = [ LLAMA_CLI_PATH,
                "-m", str(Config.MODEL_PATH),
                "--ctx-size", str(Config.N_CTX),
                "--n-predict", str(Config.MAX_GENERATION_TOKENS),
                "--threads", str(Config.N_THREADS),
                "--gpu-layers", str(Config.N_GPU_LAYERS),
                "--temp", str(Config.TEMPERATURE),
                "--top-p", str(Config.TOP_P),
                "--repeat-penalty", str(Config.REPEAT_PENALTY),
                "--frequency-penalty", str(Config.FREQUENCY_PENALTY),
                "--presence-penalty", str(Config.PRESENCE_PENALTY),
                "--chat-template-file", str(Config.TEMPLATE_PATH),
                "--system-prompt", system_prompt,
                "--prompt", user_prompt
              ]
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        full_out = result.stdout or ""
        print("=== raw stdout ===\n", full_out)

        # Clean up the generated text
        # Isolate the assistant’s output
        marker = f"{user_prompt}assistant"
        full_text = full_out.split(marker, 1)[1] if marker in full_out else full_out
        # Remove everything after the EOF sentinel
        text = full_text.split("> EOF by user", 1)[0].strip()
        # Split into paragraphs on blank lines
        paras = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        # Always take the first two paragraphs
        selected = paras[:2]
        # If a third paragraph exists and is exactly the GAME OVER marker, include it
        if len(paras) > 2 and paras[2].strip() == "GAME OVER - Try again? :)":
            selected.append(paras[2].strip())
        # Collapse all line breaks into single spaces
        generated = ' '.join(selected)

        # Count tokens for this new paragraph
        token_cost = count_tokens(generated)

        # Persist into SQLite, including token_cost
        with write_connection() as conn:
            # find next paragraph_index
            cur = conn.execute(
                "SELECT COALESCE(MAX(paragraph_index), 0) + 1 "
                "FROM story_paragraphs WHERE story_id = ?",
                ("continue_without_UserAction",)
            )
            next_index = cur.fetchone()[0]

            # INSERT and get last row id
            insert_cur = conn.execute(
                """
                INSERT INTO story_paragraphs
                  (story_id, paragraph_index, content, token_cost)
                VALUES (?, ?, ?, ?)
                """,
                ("continue_without_UserAction", next_index, generated, token_cost)
            )
            paragraph_id = insert_cur.lastrowid

        # Return id & content
        return {"id": paragraph_id, "content": generated, "story_id": "continue_without_UserAction"}

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] llama-cli exited with code {e.returncode}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
