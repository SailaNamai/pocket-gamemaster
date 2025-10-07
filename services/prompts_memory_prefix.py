# services.prompts_memory_prefix.py

from services.DB_token_cost import update_memory_costs
from services.DB_access_pipeline import write_connection

def write_memory_prefix():
    """
    Writes prefixes for "on the fly" generated memories to DB:
    table: memory
      mid_memory_hardcode     = "These are the condensed mid term story events:"
      long_memory_hardcode    = "These are the long term retained facts:"
    """
    long_prefix = "These are the long term retained facts:"
    mid_prefix  = "These are the condensed mid term story events:"

    with write_connection() as conn:
        cursor = conn.cursor()
        sql = """
        INSERT INTO memory (id, mid_memory_hardcode, long_memory_hardcode)
        VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            mid_memory_hardcode  = excluded.mid_memory_hardcode,
            long_memory_hardcode = excluded.long_memory_hardcode;
        """
        cursor.execute(sql, (mid_prefix, long_prefix))

    update_memory_costs()



