# services.prompts_summarize_from_player_action.py

from services.DB_access_pipeline import write_connection
from services.DB_token_cost import count_tokens

def get_rules_hardcode():
    return """
Memory Weighting Rules:\n
"""
def get_rules():
    return """
Importance Levels:
- Very High: Major narrative climaxes like marriage, deaths of important NPCs, finished story arcs...
- High: Events that directly advance the narrative or alter key relationships
- Medium: Progress in side narratives and changes in inventory or resources
- Low: Symbolism and minor details
- Very Low: Purely descriptive or flavor text

Retention Priorities:
- Player choices and their immediate outcomes  
- Introduction or departure of major NPCs or factions  
- Significant world-state shifts (new locations, alliances, resources)  
- Emotions that accompany the events
- Specific locations
"""

def write_mid_memory_prompts():
    """
    Writes all mid-memory summarization prompts into mid_memory_bucket,
    computes token costs for each prompt, and updates the singleton row.
    """
    # Generate prompt
    rules_hardcode = get_rules_hardcode()
    rules_user = get_rules()

    # Compute token costs for each prompt
    cost_rules_hardcode = count_tokens(rules_hardcode)
    cost_rules_user = count_tokens(rules_user)

    # Sum up for the bucket’s total cost
    total_cost = (
            cost_rules_hardcode
            + cost_rules_user
    )

    with write_connection() as conn:
        cursor = conn.cursor()
        sql = """
        INSERT INTO mid_memory_bucket (id, rules_hardcode, rules, token_cost)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            rules_hardcode = excluded.rules_hardcode,
            rules          = excluded.rules,
            token_cost     = excluded.token_cost;
        """
        cursor.execute(sql, (rules_hardcode, rules_user, total_cost))

    return