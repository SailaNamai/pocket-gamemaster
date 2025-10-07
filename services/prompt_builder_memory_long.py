# services.prompt_builder_memory_long.py

from services.llm_config import GlobalVars
from services.DB_access_pipeline import connect
from services.prompt_builder_tag_cloud import tag_scoring
from typing import Dict, Any, List, Tuple

def build_long_memory() -> str:
    """
    Assemble long-term memory:
      - Query story_paragraphs newest → oldest
      - Select entries whose tags include importance of High or Very High
      - Append summaries until token budget is reached
      - Return collected summaries in oldest → to the newest (chronological)
    """
    conn = connect(readonly=True)
    try:
        cursor = conn.cursor()
        cursor.execute("""
                SELECT id,
                       summary,
                       summary_token_cost
                  FROM story_paragraphs
                 ORDER BY id DESC
            """)
        rows = cursor.fetchall()
    finally:
        conn.close()

    """
    Tagging
    """
    scored_summary = tag_scoring() # dict. example id: 9: {'id': 9, 'importance': 'High', 'total_score': 4.6}
    ordered_medium, ordered_high, ordered_very_high = _order_by_importance(scored_summary)

    # long_memory: List[str] = []
    long_memory = _fill_budget(rows, ordered_medium, ordered_high, ordered_very_high)

    if not long_memory:
        return "None yet."

    # reverse to oldest → newest and return joined summaries
    chronological = list(reversed(long_memory))
    return "\n\n".join(s for s in chronological if isinstance(s, str))

def _fill_budget(rows, ordered_medium, ordered_high, ordered_very_high):
    """
    Select summaries from ordered_very_high then ordered_high until GlobalVars.tc_budget_long_memories is reached.
    Returns a list of summary strings ordered newest->oldest (build_long_memory will reverse to oldest->newest).
    """
    total_cost = 0
    budget = int(GlobalVars.tc_budget_long_memories)
    if budget <= 0:
        return []

    # map rows by id; if summary_token_cost is None treat it as 0
    rows_map = {
        int(r[0]): (r[1] if r[1] is not None else "", int(r[2]) if r[2] is not None else 0)
        for r in rows
    }

    selected = []
    picked = set()

    def _add(rec):
        nonlocal total_cost
        rid = int(rec["id"])
        if rid in picked:
            return
        summary, cost = rows_map[rid]
        cost = int(cost)
        if total_cost + cost > budget:
            return
        picked.add(rid)
        total_cost += cost
        selected.append((rid, summary))

    for rec in ordered_very_high:
        _add(rec)
        if total_cost >= budget:
            break

    if total_cost < budget:
        for rec in ordered_high:
            _add(rec)
            if total_cost >= budget:
                break

    if total_cost < budget:
        for rec in ordered_medium:
            _add(rec)
            if total_cost >= budget:
                break

    # Return newest->oldest; build_long_memory will reverse to chronological order
    selected.sort(key=lambda x: -x[0])
    return [s for (_id, s) in selected]

def _order_by_importance(scored_summary: Dict[Any, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Split scored_summary into two ordered lists: High and Very High importance.
    Returns (high_list, very_high_list).
    Each list is sorted by 'total_score' descending then by 'id' ascending.
    Accepts a dict mapping ids to record dicts or a list of record dicts.
    """
    if not scored_summary:
        return [], [], []

    # Normalize input to a list of records
    if isinstance(scored_summary, dict):
        records = list(scored_summary.values())
    elif isinstance(scored_summary, list):
        records = scored_summary
    else:
        raise TypeError("scored_summary must be a dict or a list of dicts")

    def norm_importance(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().lower().replace("_", " ")

    def score_key(rec: Dict[str, Any]) -> float:
        try:
            return float(rec.get("total_score", 0.0))
        except Exception:
            return 0.0

    def id_key(rec: Dict[str, Any]) -> Any:
        return rec.get("id", 0)

    very_high = []
    high = []
    medium = []

    for r in records:
        importance = norm_importance(r.get("importance"))
        if importance in ("very high", "veryhigh", "vhigh", "very-high"):
            very_high.append(r)
        elif importance == "high":
            high.append(r)
        elif importance == "medium":
            medium.append(r)

    # Sort by total_score descending then id ascending for deterministic ordering
    very_high_sorted = sorted(very_high, key=lambda x: (-score_key(x), id_key(x)))
    high_sorted = sorted(high, key=lambda x: (-score_key(x), id_key(x)))
    medium_sorted = sorted(medium, key=lambda x: (-score_key(x), id_key(x)))

    return high_sorted, very_high_sorted, medium_sorted