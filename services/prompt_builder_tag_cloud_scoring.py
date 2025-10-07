# services.prompt_builder_tag_cloud_scoring

from services.llm_config import GlobalVars # tc_budget_long_memories, Location_Weight, Character_Weight, Emotion_Weight, State_Weight, log_folder
from typing import Dict, Any
from pathlib import Path
import json

# --- Pipeline orchestrator ---
def rate_tag_cloud(tag_cloud: Dict[int, Dict[str, Any]],
                   tag_recent: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """
    Pipeline: initialize entries, then run each rating helper in sequence.
    """
    debug = True

    # initialize base structure
    scored: Dict[int, Dict[str, Any]] = {}
    for pid, tags in (tag_cloud or {}).items():
        if not isinstance(tags, dict):
            scored[pid] = {
                "id": pid,
                "importance": None,
                "total_score": 0.0,
                "location_score": 0.0,
                "character_score": 0.0,
                "emotion_score": 0.0,
                "state_score": 0.0,
            }
        else:
            scored[pid] = {
                "id": pid,
                "importance": tags.get("importance"),
                "total_score": 0.0,
                "location_score": 0.0,
                "character_score": 0.0,
                "emotion_score": 0.0,
                "state_score": 0.0,
            }

    # run pipeline
    scored = rate_cloud_location(scored, tag_recent, tag_cloud)
    scored = rate_cloud_emotion(scored, tag_recent, tag_cloud)
    scored = rate_cloud_state(scored, tag_recent, tag_cloud)
    scored = rate_cloud_character(scored, tag_recent, tag_cloud)
    if debug: _debug_helper(scored)
    return scored

"""
Individual rating helpers
"""
def rate_cloud_location(tag_cloud_scored, tag_recent, tag_cloud):
    """
    Add location_score to each entry and update total_score.

    Scoring rules:
    - Exact match between recent location and cloud location: +1.0
    - Partial match: if any single word from recent location appears in cloud location (or vice versa), +0.5
    """

    # Collect all "recent" location values from tag_recent
    recent = []
    for _, tags in (tag_recent or {}).items():
        if isinstance(tags, dict):
            recent += _to_list(tags.get("location"))
    recent = [r.lower() for r in recent if r]

    scored = {}
    for pid, entry in (tag_cloud_scored or {}).items():
        e = dict(entry) if isinstance(entry, dict) else {}

        # Get the "cloud" tags for this pid (the cleaned source of truth)
        cloud_tags = tag_cloud.get(pid) if isinstance(tag_cloud, dict) else None
        vals = [v.lower() for v in _to_list(cloud_tags.get("location"))] if isinstance(cloud_tags, dict) else []

        score = 0.0
        for r in recent:
            for v in vals:
                if not r or not v:
                    continue
                if r == v:
                    # Exact match
                    score += 1.0
                else:
                    # Partial word-level match
                    r_words = set(r.split())
                    v_words = set(v.split())
                    # Check overlap
                    overlap = r_words & v_words
                    if overlap:
                        score += 0.5

        # Store the location score
        e["location_score"] = score
        e["total_score"] = float(e.get("total_score", 0.0)) + score
        scored[pid] = e

    return scored

def rate_cloud_emotion(tag_cloud_scored, tag_recent, tag_cloud):
    """
    Add emotion_score to each entry and update total_score.
    Can actually probably stay at 1 per emotion.
    Weigh by emotional importance?
    I don't think that is a good idea - the narrative might suffer and turn the player "whiny" or whatever.
    """
    recent = []
    for _, tags in (tag_recent or {}).items():
        if isinstance(tags, dict):
            recent += _to_list(tags.get("emotion"))
    recent = [r.lower() for r in recent]

    scored = {}
    for pid, entry in (tag_cloud_scored or {}).items():
        e = dict(entry) if isinstance(entry, dict) else {}
        cloud_tags = tag_cloud.get(pid) if isinstance(tag_cloud, dict) else None
        vals = [v.lower() for v in _to_list(cloud_tags.get("emotion"))] if isinstance(cloud_tags, dict) else []

        score = sum(1.0 for r in recent if r in vals)
        e["emotion_score"] = score
        e["total_score"] = float(e.get("total_score", 0.0)) + score
        scored[pid] = e
    return scored

def rate_cloud_state(tag_cloud_scored, tag_recent, tag_cloud):
    """
    Add state_score to each entry and update total_score.

    Scoring rules:
    - Exact match between recent state and cloud state: +1.0
    - Partial match: if any single word from recent state appears in cloud state (or vice versa), +0.5
      (multiple overlaps can stack)
    """

    # Collect all recent state tags
    recent = []
    for _, tags in (tag_recent or {}).items():
        if isinstance(tags, dict):
            recent += _to_list(tags.get("state"))
    recent = [r.lower() for r in recent if r]

    scored = {}
    for pid, entry in (tag_cloud_scored or {}).items():
        e = dict(entry) if isinstance(entry, dict) else {}

        # Get this entry's state values
        cloud_tags = tag_cloud.get(pid) if isinstance(tag_cloud, dict) else None
        vals = [v.lower() for v in _to_list(cloud_tags.get("state"))] if isinstance(cloud_tags, dict) else []

        score = 0.0
        for r in recent:
            for v in vals:
                if not r or not v:
                    continue
                if r == v:
                    # Exact match
                    score += 1.0
                else:
                    # Partial word-level match
                    r_words = set(r.split())
                    v_words = set(v.split())
                    overlap = r_words & v_words
                    if overlap:
                        score += 0.5 * len(overlap)  # stackable partial matches

        # Store results
        e["state_score"] = score
        e["total_score"] = float(e.get("total_score", 0.0)) + score
        scored[pid] = e

    return scored

def rate_cloud_character(tag_cloud_partially_scored, tag_recent, tag_cloud):
    """
    Add character_score to each scored entry and update total_score.
    - Exact name matches add 1.0 per match.
    - Partial matches (one name contains the other) add 0.5 per match.
    """
    # helper to normalise various character tag shapes into a list of names
    def _to_list(value):
        if value is None:
            return []
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            return parts
        if isinstance(value, (list, tuple, set)):
            return [str(p).strip() for p in value if p is not None and str(p).strip()]
        return [str(value).strip()]

    # collect recent character names (lowercased)
    recent_chars = []
    for _, recent_tags in (tag_recent or {}).items():
        if not isinstance(recent_tags, dict):
            continue
        recent_chars += _to_list(recent_tags.get("character"))
    recent_chars = [r.lower() for r in recent_chars]

    scored: Dict[int, Dict[str, Any]] = {}
    for pid, scored_entry in (tag_cloud_partially_scored or {}).items():
        # ensure we copy the incoming entry to avoid mutation
        entry = dict(scored_entry) if isinstance(scored_entry, dict) else {}
        char_score = 0.0

        cloud_tags = tag_cloud.get(pid) if isinstance(tag_cloud, dict) else None
        cloud_chars = _to_list(cloud_tags.get("character")) if isinstance(cloud_tags, dict) else []
        cloud_chars_l = [c.lower() for c in cloud_chars]

        for c in cloud_chars_l:
            for r in recent_chars:
                if not c or not r:
                    continue
                if c == r:
                    char_score += 1.0
                elif c in r or r in c:
                    char_score += 0.5

        entry["character_score"] = char_score
        entry["total_score"] = float(entry.get("total_score", 0.0)) + char_score
        scored[pid] = entry

    return scored

def weigh_scores(tag_cloud_scored):
    """
    Multiply each *_score by the corresponding GlobalVars weight,
    round each weighted component and the total to 2 decimals
    """
    if not isinstance(tag_cloud_scored, dict):
        return {}

    def _to_float(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    weights = {
        "location_score": _to_float(getattr(GlobalVars, "Location_Weight", 1.0)),
        "character_score": _to_float(getattr(GlobalVars, "Character_Weight", 1.0)),
        "emotion_score": _to_float(getattr(GlobalVars, "Emotion_Weight", 1.0)),
        "state_score": _to_float(getattr(GlobalVars, "State_Weight", 1.0)),
    }

    weighed: Dict[int, Dict[str, Any]] = {}
    for pid, entry in tag_cloud_scored.items():
        if not isinstance(entry, dict):
            weighed[pid] = entry
            continue

        e = dict(entry)  # shallow copy to avoid mutating input
        total = 0.0
        for score_key, weight in weights.items():
            raw = _to_float(e.get(score_key, 0.0))
            weighted = round(raw * weight, 2)
            e[score_key] = weighted
            total += weighted

        total = round(total, 2)
        e["total_score"] = total
        e["total_score_str"] = f"{total:.2f}"
        weighed[pid] = e

    return weighed

def _to_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else []
    if isinstance(value, (list, tuple, set)):
        return [str(p).strip() for p in value if p is not None and str(p).strip()]
    return [str(value).strip()]

def _debug_helper(scored):
    """
    Write the scored dictionary to a debug log file.
    Each entry is printed with its id and score breakdown.
    """
    log_dir: Path = GlobalVars.log_folder
    log_file: Path = log_dir / "tag_scoring.log"

    log_dir.mkdir(parents=True, exist_ok=True)

    with log_file.open('w', encoding='utf-8') as log_f:
        log_f.write("=== By id and score ===\n")

        if not isinstance(scored, dict):
            log_f.write("No scored data (not a dict)\n")
            return

        for pid, entry in scored.items():
            log_f.write(f"\n--- id: {pid} ---\n")
            if not isinstance(entry, dict):
                log_f.write(f"{entry}\n")
                continue

            # Pretty print each key/value
            for k, v in entry.items():
                log_f.write(f"{k}: {v}\n")

        # Optionally: dump the whole structure as JSON at the end
        log_f.write("\n=== full JSON dump ===\n")
        try:
            log_f.write(json.dumps(scored, indent=2, ensure_ascii=False))
        except Exception as e:
            log_f.write(f"JSON dump failed: {e}\n")

    return
