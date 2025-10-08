# prompt_builder_tag_cloud.py

import sqlite3
import json
import re
from typing import Dict, Any, Optional, Iterable

from services.DB_access_pipeline import connect
from services.prompt_builder_tag_cloud_scoring import rate_tag_cloud, weigh_scores

def tag_scoring():
    debug = True
    # example print output of tag_cloud/tag_recent:
    # 39: {'location': 'Eastern Grove', 'character': ['Master Lyrien', 'Kaelin Darkhaven', 'Elara'], 'importance': 'High', 'emotion': 'anticipation', 'state': 'questing'},
    tag_recent = _get_tag_recent()
    tag_cloud_raw = _get_tag_cloud()
    tag_cloud_cleaned = _scrub_character_tag(tag_cloud_raw)
    # rate and weigh
    tag_cloud_scored = rate_tag_cloud(tag_cloud_cleaned, tag_recent) # we don't need to clean tag_recent (no matches for what we removed from the cloud)
    tag_cloud_weighed = weigh_scores(tag_cloud_scored)
    # cut to essentials
    tag_cloud_pruned = _prune(tag_cloud_weighed)
    if debug: _debug_printer(tag_cloud_cleaned, tag_recent, tag_cloud_weighed, tag_cloud_pruned)
    # example id of tag_cloud_pruned:
    # 9: {'id': 9, 'importance': 'High', 'total_score': 4.6}
    return tag_cloud_pruned

def _prune(tag_cloud_weighed):
    """
    Reduce each scored entry to only: 'id', 'importance', 'total_score'.
    Returns a mapping: pid -> {'id': pid, 'importance': ..., 'total_score': float}
    """
    if not isinstance(tag_cloud_weighed, dict):
        return {}

    def _to_float(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    pruned: Dict[int, Dict[str, Any]] = {}
    for pid, entry in tag_cloud_weighed.items():
        if not isinstance(entry, dict):
            pruned[pid] = {"id": pid, "importance": None, "total_score": 0.0}
            continue

        importance = entry.get("importance")
        total_score = _to_float(entry.get("total_score", 0.0))

        pruned[pid] = {
            "id": pid,
            "importance": importance,
            "total_score": total_score,
        }

    return pruned

def _scrub_character_tag(tag_cloud: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """
    Clean the character tag:
    - remove banned entries (case-insensitive)
    - strip any trailing parenthetical qualifiers, e.g. "Marlin (met at store)" -> "Marlin"
    """

    banned = {
        "i", "you",
        "narrator", "narrator", "narrator", "narrator",
        "narrator", "narrator",
        "player", "<PlayerAction>", "player character", "player character",
        "player character", "player"
    }

    cleaned_cloud: Dict[int, Dict[str, Any]] = {}

    def _iter_items(value: Any) -> Iterable[str]:
        if value is None:
            return []
        if isinstance(value, str):
            # allow comma separated names as fallback
            return [p.strip() for p in value.split(",") if p.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(p).strip() for p in value if p is not None and str(p).strip()]
        return [str(value).strip()]

    def _unique_preserve_order(seq: Iterable[str]) -> list:
        seen = set()
        out = []
        for s in seq:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    def _strip_parenthetical(name: str) -> str:
        # Remove all "(...)" groups anywhere in the string
        return re.sub(r"\s*\([^)]*\)", "", name).strip()

    for pid, tags in tag_cloud.items():
        if not isinstance(tags, dict):
            cleaned_cloud[pid] = tags
            continue

        tags_copy = dict(tags)  # shallow copy to avoid mutating input
        if "character" in tags_copy:
            raw = tags_copy.get("character")
            items = list(_iter_items(raw))

            # normalize by stripping parentheticals
            normalized = [_strip_parenthetical(itm) for itm in items]

            # filter banned entries case-insensitively
            filtered = [itm for itm in normalized if itm.lower() not in banned]

            # dedupe while preserving order
            filtered = _unique_preserve_order(filtered)

            if not filtered:
                tags_copy["character"] = None
            elif len(filtered) == 1:
                tags_copy["character"] = filtered[0]
            else:
                tags_copy["character"] = filtered

        cleaned_cloud[pid] = tags_copy

    return cleaned_cloud


def _get_tag_recent() -> Dict[int, Dict[str, Any]]:
    """
    Return an id-keyed mapping for the most recent non-empty tags_recent row:
      { id: { <normalized tags> } }
    Returns {} when nothing found or on parse error.
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT id, tags_recent FROM story_paragraphs "
            "WHERE tags_recent IS NOT NULL AND tags_recent != '' "
            "ORDER BY id DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            return {}
        raw_json = row["tags_recent"]
        try:
            parsed = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except json.JSONDecodeError:
            return {}
        return {int(row["id"]): _normalize_tags(parsed)}
    finally:
        conn.close()

def _get_tag_cloud(limit: Optional[int] = None) -> Dict[int, Dict[str, Any]]:
    """
    Return an id-keyed mapping of tags from the 'tags' column:
      { id: { <normalized tags> }, ... }
    """
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        sql = "SELECT id, tags FROM story_paragraphs WHERE tags IS NOT NULL AND tags != '' ORDER BY id DESC"
        if isinstance(limit, int) and limit > 0:
            sql += f" LIMIT {int(limit)}"
        cur.execute(sql)
        rows = cur.fetchall()
        cloud: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            raw_json = row["tags"]
            try:
                parsed = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
            except json.JSONDecodeError:
                continue
            cloud[int(row["id"])] = _normalize_tags(parsed)
        return cloud
    finally:
        conn.close()

def _normalize_tags(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    normalized: Dict[str, Any] = {}
    for k, v in raw.items():
        if isinstance(v, str):
            v = v.strip()
            if ';' in v:
                parts = [p.strip() for p in v.split(';') if p.strip()]
                normalized[k] = parts
            elif v == "":
                normalized[k] = None
            else:
                normalized[k] = v
        else:
            normalized[k] = v
    return normalized

def _debug_printer(tag_cloud_cleaned, tag_recent, tag_cloud_scored, tag_cloud_pruned):
    print("--- TAG_CLOUD ---")
    print(tag_cloud_cleaned)
    print("--- TAG_RECENT ---")
    print(tag_recent)
    print("--- CLOUD SCORING ---")
    print(tag_cloud_scored)
    print("--- PRUNED VERSION ---")
    print(tag_cloud_pruned)
    return