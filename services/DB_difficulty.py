# services.DB_difficulty.py

from services.DB_access_pipeline import connect, write_connection

def update_difficulty(difficulty: str):
    with write_connection() as conn:
        cursor = conn.cursor()
        sql = """
        INSERT INTO action_eval_bucket (id, difficulty)
        VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET
            difficulty = excluded.difficulty
        """
        cursor.execute(sql, (difficulty,))
    return

def get_difficulty():
    conn = connect(readonly=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT difficulty FROM action_eval_bucket WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()

def write_difficulty():
    """
    Ensure the difficulty field has a value.
    If the row is empty (or the column is NULL), write the default
    value ``"medium"``; otherwise leave the existing value untouched.
    """
    # Check current value
    current = get_difficulty()

    # If nothing is stored, insert the default
    if not current:
        update_difficulty("medium")