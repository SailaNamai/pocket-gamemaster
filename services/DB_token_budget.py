# services.DB_token_budget.py

from services.llm_config import Config, GlobalVars
from services.DB_access_pipeline import write_connection, connect
from services.DB_token_cost import get_prompt_cost


from typing import Optional

def write_budget(n_ctx, recent, mid, long):
    """
    Writes user custom settings to db,
    otherwise uses pre-defined settings
    """
    if not check_sanity(n_ctx, recent, mid, long):
        return
    else: # write them
        long_allocated = _distribute_remaining(n_ctx, recent, mid, long)
        with write_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO token_budget(id) VALUES (1)")
            conn.execute("""
                        UPDATE token_budget
                           SET budget_max = ?,
                               recent_budget = ?,
                               mid_budget = ?,
                               long_budget = ?
                         WHERE id = 1
                    """, (n_ctx, recent, mid, long_allocated)
            )
    return

def update_budget():
    prompt_token_cost = int(get_prompt_cost() or 0)
    gen_budget = int(Config.MAX_GENERATION_TOKENS or 0)
    n_ctx = int(Config.N_CTX)

    with write_connection() as conn:
        # acquire immediate transaction to avoid lost updates with concurrent writers
        conn.execute("BEGIN IMMEDIATE")

        # read current budgets from DB (fall back to GlobalVars when missing)
        cur = conn.execute("SELECT budget_max, recent_budget, mid_budget, long_budget FROM token_budget WHERE id = 1").fetchone()
        if cur and cur[0] is not None:
            db_budget_max, db_recent, db_mid, db_long = cur
            db_recent = int(db_recent or GlobalVars.tc_budget_recent_paragraphs)
            db_mid = int(db_mid or GlobalVars.tc_budget_mid_memories)
            db_long = int(db_long or GlobalVars.tc_budget_long_memories)
            db_budget_max = int(db_budget_max or n_ctx)
        else:
            # fallback defaults if table is empty
            db_budget_max = n_ctx
            db_recent = int(GlobalVars.tc_budget_recent_paragraphs)
            db_mid = int(GlobalVars.tc_budget_mid_memories)
            db_long = int(GlobalVars.tc_budget_long_memories)
            conn.execute("INSERT OR IGNORE INTO token_budget(id) VALUES (1)")

        # compute remaining based on the authoritative DB values
        remaining = db_budget_max - (db_recent + db_mid + db_long + prompt_token_cost + gen_budget)

        # compute new long and clamp
        new_long = max(0, db_long + remaining)

        # update long_budget only if changed
        if new_long != db_long:
            conn.execute("UPDATE token_budget SET long_budget = ? WHERE id = 1", (new_long,))

        # commit happens when write_connection closes (context manager)



def _distribute_remaining(n_ctx, recent, mid, long):
    """
    Determine unused token budget and allocate remainder to long
    """
    # get token costs
    prompt_token_cost = get_prompt_cost()
    gen_budget = Config.MAX_GENERATION_TOKENS

    # determine unused budget and add to long
    remaining = n_ctx - (recent + mid + long + prompt_token_cost + gen_budget)
    long_allocated = long + remaining

    return long_allocated

def check_sanity(n_ctx, recent, mid, long_):
    """
    Return False when we need to refuse what the user entered.
    Return True when we pass the sanity check.
    """
    # ensure inputs are integers
    try:
        n_ctx = int(n_ctx)
        recent = int(recent)
        mid = int(mid)
        long_ = int(long_)
    except (TypeError, ValueError):
        return False

    # get token costs (ensure these return ints)
    prompt_token_cost = int(get_prompt_cost() or 0)
    gen_budget = int(Config.MAX_GENERATION_TOKENS or 0)

    # not enough budget
    if n_ctx - (recent + mid + long_ + prompt_token_cost + gen_budget) < 0:
        return False

    # too large context
    if n_ctx > 8000:
        return False

    # any of the history buckets must be positive
    if recent <= 0 or mid <= 0 or long_ <= 0:
        return False

    return True


"""
Initial state
"""
def write_initial_budget():
    """
    Initial default value (services.llm_config) write to DB
    """
    if not _db_check_budget():
        return
    else:
        # get default values
        n_ctx = int(Config.N_CTX)
        recent = int(GlobalVars.tc_budget_recent_paragraphs)
        mid = int(GlobalVars.tc_budget_mid_memories)
        long = int(GlobalVars.tc_budget_long_memories)
        # write them
        with write_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO token_budget(id) VALUES (1)")
            conn.execute("""
                UPDATE token_budget
                   SET budget_max = ?,
                       recent_budget = ?,
                       mid_budget = ?,
                       long_budget = ?
                 WHERE id = 1
                """,
                (n_ctx, recent, mid, long)
            )
        return

def _db_check_budget() -> bool:
    """
    Return True when any of the four budget fields are missing or empty.
    Return False when all four fields are present and truthy (non-empty, non-None).
    """
    conn = connect(readonly=True)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT budget_max, recent_budget, mid_budget, long_budget
              FROM token_budget
             WHERE ID = 1
            """
        )
        row: Optional[tuple] = cur.fetchone()
    finally:
        conn.close()

    # If no row found that's an "empty" state
    if not row:
        return True

    budget_max, recent_budget, mid_budget, long_budget = row

    # Treat None or empty string as empty; treat 0 as a valid (non-empty) value.
    def is_empty(value) -> bool:
        return value is None or (isinstance(value, str) and value.strip() == "")

    return any(is_empty(v) for v in (budget_max, recent_budget, mid_budget, long_budget))