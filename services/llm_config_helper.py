# services.llm_config_helper.py

from services.DB_access_pipeline import connect
import logging
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