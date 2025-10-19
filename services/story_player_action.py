# services.story_player_action.py

import subprocess
import sys
import difflib

from services.llm_config import Config
from services.llm_config_helper import output_cleaner, normalize_output, remove_truncated, close_quotes, clean_tags
from services.DB_access_pipeline import write_connection
from services.prompt_builder_story_player_action import get_story_player_action_prompts
from services.DB_token_cost import count_tokens


LLAMA_CLI_PATH = Config.LLAMA_CLI

def is_close_match(a, b, threshold=0.8):
    return difflib.SequenceMatcher(None, a, b).ratio() >= threshold

def generate_player_action():
    try:
        # Build prompts
        system_prompt, user_prompt = get_story_player_action_prompts()

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
            encoding='utf-8',
            errors='replace',
            check=True
        )
        full_out = result.stdout or ""
        print("=== raw stdout ===\n", full_out)

        # Clean & normalize
        generated = output_cleaner(full_out, user_prompt)
        normalized = normalize_output(generated)
        del_truncated = remove_truncated(normalized)
        cleaned_tags = clean_tags(del_truncated)
        selected_sentences = close_quotes(cleaned_tags)

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
                ("continue_without_UserAction", next_index, selected_sentences, token_cost)
            )
            paragraph_id = insert_cur.lastrowid

        # Return id & content
        return {"id": paragraph_id, "content": selected_sentences, "story_id": "continue_without_UserAction"}

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] llama-cli exited with code {e.returncode}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)

    except Exception as e:
        print("-- player_action error --")
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)