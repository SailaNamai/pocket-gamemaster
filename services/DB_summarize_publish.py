# services.DB_summarize_publish.py
# This is for publishing memory to the front end

from services.llm_config import GlobalVars
from services.DB_access_pipeline import connect

def publish_mid_memory():
    conn = connect(readonly=True)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id,
                   token_cost,
                   summary_from_action,
                   summary_token_cost
              FROM story_paragraphs
             ORDER BY id DESC
        """)
        rows = cursor.fetchall()
    finally:
        conn.close()

    recent_sum = 0
    skip_idx = None
    for i, (row_id, tok_s, _, _) in enumerate(rows):
        try:
            tc = int(tok_s)
        except (TypeError, ValueError):
            tc = 0

        if recent_sum + tc > GlobalVars.tc_budget_recent_paragraphs:
            skip_idx = i + 1
            break

        recent_sum += tc

    if skip_idx is None:
        skip_idx = 0

    mid_sum = 0
    mids = []
    for row_id, tok_s, sum_action, sum_tok_s in rows[skip_idx:]:
        if not sum_action:
            continue

        try:
            stc = int(sum_tok_s)
        except (TypeError, ValueError):
            stc = 0

        if mid_sum + stc > GlobalVars.tc_budget_mid_memories:
            continue

        mid_sum += stc
        mids.append((row_id, sum_action))

    if not mids:
        return "None yet."

    # Build HTML paragraphs in chronological order
    html = "".join(
        f'<p data-paragraph-id="{row_id}">{summary}</p>'
        for row_id, summary in reversed(mids)
    )
    return html

def publish_long_memory() -> str:
    """
    Assemble long-term memory by:
      - Querying story_paragraphs newest → oldest
      - Collecting all non-empty summaries
      - Returning the collected summaries wrapped in <p> tags with their id
    """
    conn = connect(readonly=True)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, summary
              FROM story_paragraphs
             ORDER BY id DESC
        """)
        rows = cursor.fetchall()
    finally:
        conn.close()

    long_memory = []
    for row in rows:
        try:
            row_id, summary_text = row
        except ValueError:
            continue

        if not summary_text or not isinstance(summary_text, str):
            continue

        long_memory.append((row_id, summary_text))

    if not long_memory:
        return "None yet."

    html = "".join(
        '<p data-paragraph-id="{rid}">{content}</p>'.format(
            rid=rid,
            content="<br>".join(
                line.lstrip("- ").strip()
                for line in summary_text.splitlines()
                if line.strip()
            )
        )
        for rid, summary_text in reversed(long_memory)
    )
    return html

