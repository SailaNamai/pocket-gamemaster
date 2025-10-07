# services/count_tokens/count.py

"""
Put any text you want to count into count_me.log and save it.
Then open a terminal from the 'count_tokens' folder and do python count.py
"""

import sys
from pathlib import Path

# 1. Ensure project root is on the import path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from llama_cpp import Llama
from services.llm_config import Config
from typing import Optional

# initialize a real Llama tokenizer instance
llm: Llama = Llama(model_path=str(Config.MODEL_PATH))

def _count_tokens(text: Optional[str]) -> int:
    """
    Returns how many tokens llama.cpp would "consume" for `text`.
    Safely handles None and empty/whitespace-only strings.
    """
    if not text:
        return 0

    # Normalise to a str in case callers pass bytes by mistake
    if isinstance(text, bytes):
        b = text
    else:
        b = str(text).encode('utf-8')

    try:
        token_ids = llm.tokenize(b, add_bos=False)
    except Exception:
        # If tokenizer fails for any reason, fall back to conservative estimate 0
        return 0

    return len(token_ids)

def main():
    log_path = Path(__file__).parent / "count_me.log"
    if not log_path.exists():
        print(f"Error: {log_path.name} not found", file=sys.stderr)
        sys.exit(1)

    # 3. Read the log file
    text = log_path.read_text(encoding="utf-8")

    # 4. Count tokens and print
    num_tokens = _count_tokens(text)
    print(f"============")
    print(f"Token count: {num_tokens}")
    print(f"============")

if __name__ == "__main__":
    main()
