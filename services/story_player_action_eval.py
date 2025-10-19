# services.story_player_action_eval.py

import subprocess
import sys


from services.llm_config import Config
from services.llm_config_helper import output_cleaner
from services.DB_access_pipeline import write_connection
from services.prompt_builder_eval_action import get_eval_player_action_prompts
from services.DB_token_cost import count_tokens

LLAMA_CLI_PATH = Config.LLAMA_CLI

def evaluate_player_action():
    try:
        # Build prompts
        system_prompt, user_prompt = get_eval_player_action_prompts()

        # Run llama-cli
        cmd = [ LLAMA_CLI_PATH,
                "-m", str(Config.MODEL_PATH_GM),
                "--ctx-size", str(Config.N_CTX),
                "--n-predict", str(Config.MAX_GENERATION_TOKENS),
                "--threads", str(Config.N_THREADS),
                "--gpu-layers", str(Config.N_GPU_LAYERS),
                "--temp", str(Config.TEMPERATURE_EVAL),
                "--top-p", str(Config.TOP_P_slave),
                "--repeat-penalty", str(Config.REPEAT_PENALTY_slave),
                "--frequency-penalty", str(Config.FREQUENCY_PENALTY_slave),
                "--presence-penalty", str(Config.PRESENCE_PENALTY_slave),
                "--chat-template-file", str(Config.TEMPLATE_PATH_GM),
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
        generated = output_cleaner(full_out, user_prompt)

        # Count tokens for this new paragraph
        token_cost = count_tokens(generated)

        # Persist into SQLite, updating the last row with outcome + token cost
        print("write_connection type:", type(write_connection))
        with write_connection() as conn:
            cur = conn.cursor()

            # find the last (highest id) paragraph
            cur.execute("SELECT MAX(id) FROM story_paragraphs")
            last_id = cur.fetchone()[0]

            if last_id is None:
                raise RuntimeError("No existing paragraph found to update")

            # update that row with outcome and token cost
            cur.execute(
                """
                UPDATE story_paragraphs
                   SET outcome = ?,
                       outcome_token_cost = ?
                 WHERE id = ?
                """,
                (generated, token_cost, last_id)
            )

        return

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] llama-cli exited with code {e.returncode}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode)

    except Exception as e:
        print("-- player_action_eval error --")
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

