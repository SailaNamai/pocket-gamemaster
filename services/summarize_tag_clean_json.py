# services.summarize_tag_clean_json.py

import json
import re

def clean_llm_json(raw: str) -> str:
    """
    Normalize slightly malformed JSON from LLM output.
    Returns a cleaned JSON string.
    """
    # --- Step 0: isolate the first JSON object only ---
    # Find the last closing brace and cut off anything after it
    if "}" in raw:
        raw = raw[: raw.rfind("}") + 1]

    # --- Step 1: fast path ---
    try:
        obj = json.loads(raw)
        return json.dumps(obj, ensure_ascii=False)
    except json.JSONDecodeError:
        pass  # fall through to cleaning

    fixed = raw.strip().strip("` \n\t")

    # --- Step 2: heuristic fixes ---
    # Fix case 1: double double-quotes inside values
    fixed = re.sub(r'""([^"]+)"', r'"\1"', fixed)

    # Fix case 2: single-quoted fragments inside values
    fixed = re.sub(r"'\s*([^']*?)\s*'", r"\1", fixed)

    # Remove stray backslashes before quotes (e.g. Marcus\' Residence)
    fixed = fixed.replace("\\'", "'")

    try:
        obj = json.loads(fixed)
    except json.JSONDecodeError:
        # As last resort, wrap in dict
        return json.dumps({"raw": raw}, ensure_ascii=False)

    # --- Step 3: normalize "state" field ---
    if "state" in obj and isinstance(obj["state"], str):
        s = obj["state"]
        s = s.replace('""', '"').replace('"', '')
        s = s.replace("';", ";").replace("'", "")
        s = re.sub(r"\s*;\s*", "; ", s)
        obj["state"] = s.strip()

    return json.dumps(obj, ensure_ascii=False)
