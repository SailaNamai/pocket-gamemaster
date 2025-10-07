# services.prompt_builder_memory_mid.py

from services.llm_config import GlobalVars
from services.DB_access_pipeline import connect

def build_mid_memory():
    """
    Assemble mid-term memory by:
      1. Finding the cut-off point where recent token_cost > tc_budget_recent_paragraphs.
         If that never happens, we start from the very newest paragraph.
      2. Scanning from that cut-off onward (i.e. older entries), pulling only summary_from_action,
         and summing summary_token_cost up to tc_budget_mid_memories. If one summary is too big,
         we skip it and keep going.
      3. Returning what we gathered, in chronological order, or "None yet." if empty.
    """
    conn = connect(readonly=True)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT token_cost,
                   summary_from_action,
                   summary_token_cost
              FROM story_paragraphs
             ORDER BY id DESC
        """)
        rows = cursor.fetchall()
    finally:
        conn.close()

    # 1) Find the index where we’ve “skipped” enough recent tokens
    recent_sum = 0
    skip_idx = None
    for i, (tok_s, _, _) in enumerate(rows):
        try:
            tc = int(tok_s)
        except (TypeError, ValueError):
            tc = 0

        # as soon as adding this paragraph would exceed the recent budget, stop skipping
        if recent_sum + tc > GlobalVars.tc_budget_recent_paragraphs:
            skip_idx = i + 1
            break

        recent_sum += tc

    # if we never hit the budget, don’t skip anything
    if skip_idx is None:
        skip_idx = 0

    # 2) Collect mid-term summaries
    mid_sum = 0
    mids = []
    for tok_s, sum_action, sum_tok_s in rows[skip_idx:]:
        if not sum_action:
            continue

        try:
            stc = int(sum_tok_s)
        except (TypeError, ValueError):
            stc = 0

        # if this single summary would overflow our mid budget, skip it
        if mid_sum + stc > GlobalVars.tc_budget_mid_memories:
            continue

        mid_sum += stc
        mids.append(sum_action)

    # 3) Return
    if not mids:
        return "None yet."

    # chronological order + blank-line separators
    return "\n\n".join(reversed(mids))

