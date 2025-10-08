# services.summarize_tag_mid.py

import subprocess
import sys

from services.summarize_tag_clean_json import clean_llm_json
from services.llm_config import Config, GlobalVars
from services.DB_access_pipeline import write_connection
from services.prompt_builder_tag_mid import get_tagging_system_prompts

LLAMA_CLI_PATH = Config.LLAMA_CLI
LOG_DIR  = GlobalVars.log_folder
LOG_FILE = 'tag_mid.log'

def summarize_create_tags():
    log_path = LOG_DIR / LOG_FILE

    # build prompts
    system_prompt, user_prompt, write_id = get_tagging_system_prompts()

    # invoke llama-cli
    cmd = [
        LLAMA_CLI_PATH,
        "-m", str(Config.MODEL_PATH),
        "--ctx-size", str(Config.N_CTX),
        "--threads", str(Config.N_THREADS),
        "--gpu-layers", str(Config.N_GPU_LAYERS),
        "--temp", str(Config.TEMPERATURE_TAGS),
        "--top-p", str(Config.TOP_P_slave),
        "--repeat-penalty", str(Config.REPEAT_PENALTY_slave),
        "--frequency-penalty", str(Config.FREQUENCY_PENALTY_slave),
        "--presence-penalty", str(Config.PRESENCE_PENALTY_slave),
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
    body = assistant_out.split("> EOF by user", 1)[0].strip()
    tags = body.strip()
    # attempt json repair
    tags_repaired = clean_llm_json(tags)

    # Log both
    with open(log_path, 'w', encoding='utf-8') as log_f:
        log_f.write("=== LLM json ===\n")
        log_f.write(tags + "\n\n")
        log_f.write("=== repaired json ===\n")
        log_f.write(tags_repaired + "\n")

    # persist: update story_paragraphs.tags
    with write_connection() as conn:

        paragraph_id = int(write_id)

        # single UPDATE
        conn.execute("""
            UPDATE story_paragraphs
               SET tags = ?
             WHERE id = ?
        """, (
            tags,
            paragraph_id,
        ))
