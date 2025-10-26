# services.llm_config_helper.py

from services.DB_access_pipeline import connect
import logging
import re

def clean_tags(text: str) -> str:
    """
    Remove any <Outcome>...</Outcome> or <PlayerAction>...</PlayerAction> spans
    from the given text. Works across multiple lines.
    - If a <PlayerAction> or <Outcome> opening tag is found when scanning from the end
      without a matching closing tag, remove that tag and everything that follows it.
    """
    # First, remove complete <Outcome>...</Outcome> and <PlayerAction>...</PlayerAction> spans
    pattern = re.compile(r"<(Outcome|PlayerAction)>.*?</\1>", re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(pattern, "", text)

    # Then, check for any trailing unclosed <PlayerAction> or <Outcome> opening tag
    for tag in ("playeraction", "outcome"):
        last_open = cleaned.lower().rfind(f"<{tag}>")
        if last_open != -1:
            # Only cut if there is no matching closing tag after it
            closing = cleaned.lower().find(f"</{tag}>", last_open)
            if closing == -1:
                cleaned = cleaned[:last_open]

    # 3. Remove any remaining <...> markup (including the brackets)
    any_tag_pat = re.compile(r"<[^>]+>")
    cleaned = re.sub(any_tag_pat, "", cleaned)

    # Collapse extra whitespace left behind
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned



def close_quotes(text: str) -> str:
    """
    Ensure that any unmatched opening double‑quote is closed
    after the final sentence boundary.

    • If the number of `"` characters is even → return text unchanged.
    • If odd → insert a missing `"` right after the final sentence-ending
      punctuation (., !, ?) if present, otherwise at the very end.
    """
    if text.count('"') % 2 == 0:
        return text

    stripped = text.rstrip()

    # Find the last sentence-ending punctuation
    match = re.search(r'[.!?](?=\s*$)', stripped)
    if match:
        # Insert quote right after the punctuation
        return stripped[:match.end()] + '"' + stripped[match.end():]
    else:
        # No sentence-ending punctuation → append at end
        return stripped + '"'

def remove_truncated(text: str) -> str:
    """
    Remove a possibly truncated final sentence.

    Keeps all complete sentences up to the last full stop (. ! ?),
    including a trailing closing quote if present.
    Drops any trailing fragment that doesn't end with sentence punctuation.
    """
    stripped = text.rstrip()

    # Match sentence-ending punctuation with optional closing quote
    # [.!?] required
    # ["']? optional closing quote
    # followed only by whitespace or EOS
    matches = list(re.finditer(r'[.!?]["\']?(?=\s|$)', stripped, re.S))

    if matches:
        last_end = matches[-1].end()
        return stripped[:last_end].strip()

    return stripped

def normalize_output(text: str) -> str:
    """
    Post-process the generated text by:
    - Dropping empty lines
    - Normalizing quote-space-quote → " - "
    - Removing any **headline** or **headline**: spans
    """
    # Collapse multiple line breaks, strip whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = " ".join(lines)

    # Normalize quote-space-quote → " - "
    text = re.sub(r'"\s+"', '" - "', text)

    # Remove **...** or **...**: (non-greedy inside)
    text = re.sub(r"\*\*[^*]+?\*\*:?", "", text)

    # Collapse extra spaces left behind
    text = re.sub(r"\s{2,}", " ", text).strip()

    return text

def output_cleaner(full_out: str, user_prompt: str) -> str:
    """
    Extracts the model's generated text from raw stdout by:
    - Removing the echoed user prompt
    - Stripping known assistant markers
    - Trimming at known end markers
    - Removing empty lines
    """
    # Find where the user prompt ends
    pos = full_out.rfind(user_prompt)
    if pos != -1:
        generated = full_out[pos + len(user_prompt):]
    else:
        generated = full_out  # fallback if not found

    # --- Flexible assistant marker parsing ---
    assistant_markers = [
        "<|start_header_id|>assistant<|end_header_id|>",  # dark sapling
        "<|im_start|>assistant",  # LLaMA / Mistral style
        "<|im_start|> assistant",  # Variant with space
        "<start_of_turn>model",   # Gemma 3 IT
        "### Response:",          # Some Alpaca/Stanford style
        "assistant",              # Generic fallback #wingless
    ]
    for marker in assistant_markers:
        if marker in generated:
            generated = generated.split(marker, 1)[1]
            break

    # Trim everything including known end markers
    end_markers = [
        "> EOF by user",
        "<|im_end|>",
        "</s>",
        "<end_of_turn>",
    ]
    for end_marker in end_markers:
        if end_marker in generated:
            generated = generated.split(end_marker, 1)[0]
            break

    # --- Remove empty lines ---
    lines = generated.splitlines()
    non_empty = [line for line in lines if line.strip()]
    cleaned = "\n".join(non_empty)

    return cleaned.strip()

"""
Token budgeting get helper
"""
def get_n_ctx() -> int:
    default = 6192
    try:
        conn = connect(readonly=True)
    except Exception:
        logging.exception("Could not open DB for token budget, using default")
        return default

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT budget_max
              FROM token_budget
             WHERE id = 1
            """
        )
        row = cur.fetchone()
        if not row:
            logging.warning("token_budget row not found, using default %d", default)
            return default

        # fetchone() may return a tuple or sqlite Row object; extract the value robustly
        if isinstance(row, (tuple, list)):
            val = row[0]
        elif isinstance(row, dict) or hasattr(row, "keys"):
            # sqlite3.Row supports mapping access
            val = row.get("budget_max", None)
        else:
            val = row

        if val is None:
            logging.warning("budget_max is NULL, using default %d", default)
            return default

        try:
            return int(val)
        except (TypeError, ValueError):
            logging.exception("Invalid budget_max value in token_budget: %r; using default", val)
            return default
    finally:
        conn.close()

def get_recent() -> int:
    default = 1500
    try:
        conn = connect(readonly=True)
    except Exception:
        logging.exception("Could not open DB for token budget, using default")
        return default

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT recent_budget
              FROM token_budget
             WHERE id = 1
            """
        )
        row = cur.fetchone()
        if not row:
            logging.warning("token_budget row not found, using default %d", default)
            return default

        # fetchone() may return a tuple or sqlite Row object; extract the value robustly
        if isinstance(row, (tuple, list)):
            val = row[0]
        elif isinstance(row, dict) or hasattr(row, "keys"):
            # sqlite3.Row supports mapping access
            val = row.get("recent_budget", None)
        else:
            val = row

        if val is None:
            logging.warning("recent_budget is NULL, using default %d", default)
            return default

        try:
            return int(val)
        except (TypeError, ValueError):
            logging.exception("Invalid recent_budget value in token_budget: %r; using default", val)
            return default
    finally:
        conn.close()

def get_mid() -> int:
    default = 1500
    try:
        conn = connect(readonly=True)
    except Exception:
        logging.exception("Could not open DB for token budget, using default")
        return default

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT mid_budget
              FROM token_budget
             WHERE id = 1
            """
        )
        row = cur.fetchone()
        if not row:
            logging.warning("token_budget row not found, using default %d", default)
            return default

        # fetchone() may return a tuple or sqlite Row object; extract the value robustly
        if isinstance(row, (tuple, list)):
            val = row[0]
        elif isinstance(row, dict) or hasattr(row, "keys"):
            # sqlite3.Row supports mapping access
            val = row.get("mid_budget", None)
        else:
            val = row

        if val is None:
            logging.warning("mid_budget is NULL, using default %d", default)
            return default

        try:
            return int(val)
        except (TypeError, ValueError):
            logging.exception("Invalid mid_budget value in token_budget: %r; using default", val)
            return default
    finally:
        conn.close()


def get_long() -> int:
    default = 1500
    try:
        conn = connect(readonly=True)
    except Exception:
        logging.exception("Could not open DB for token budget, using default")
        return default

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT long_budget
              FROM token_budget
             WHERE id = 1
            """
        )
        row = cur.fetchone()
        if not row:
            logging.warning("token_budget row not found, using default %d", default)
            return default

        # fetchone() may return a tuple or sqlite Row object; extract the value robustly
        if isinstance(row, (tuple, list)):
            val = row[0]
        elif isinstance(row, dict) or hasattr(row, "keys"):
            # sqlite3.Row supports mapping access
            val = row.get("long_budget", None)
        else:
            val = row

        if val is None:
            logging.warning("long_budget is NULL, using default %d", default)
            return default

        try:
            return int(val)
        except (TypeError, ValueError):
            logging.exception("Invalid long_budget value in token_budget: %r; using default", val)
            return default
    finally:
        conn.close()