# services.prompts_eval_action.py

from services.DB_token_cost import count_tokens
from services.DB_access_pipeline import write_connection
from services.DB_difficulty import get_difficulty

"""
We galaxy-brain cheat: easy = medium, medium = hard, hard = souls like death-march
"""

# easy = medium
def eval_action_easy():
    return """
    1.5 **Evaluation Rules (Medium Difficulty)**:
        - Identify the action category (combat, social, exploration, technical, etc.).
        - Determine relevant stats, skills, and context modifiers.
        - Compare character capability vs. challenge difficulty.
        - Apply medium bias: success requires clear advantage or strong justification.
        - If outcome is ambiguous or unsupported, default to failure.
        - Impossible actions (those that contradict established setting rules, physical laws, or available resources) always fail.
    
        Medium baseline:
            - Outcomes should balance fairness and challenge.
            - Characters succeed when their abilities or context clearly justify it.
            - Uncertain or marginal cases lean toward failure.
            - The world resists easy victories but rewards strong advantages."""

# medium = hard
def eval_action_med():
    return """
    1.5 **Evaluation Rules (Hard Difficulty)**:
        - Identify the action category (combat, social, exploration, technical, etc.)
        - Determine relevant stats, skills, and context modifiers
        - Compare character capability vs. challenge difficulty
        - Emotional state, determination, or narrative flavor may color the description of outcomes, but they must never outweigh raw capability, stats, or chance when determining success or failure.
        - Apply hard bias: success only if advantage is decisive or overwhelming
        - Partial successes or failures extract an appropriate cost
        - If outcome is ambiguous, unsupported, or only marginally justified: fail
        - Impossible actions (those that contradict established setting rules, physical laws, or available resources) always fail
        
        Hard Baseline:
            - Outcomes favor failure unless the character has overwhelming advantage. 
            - The world is harsh and resistant
            - Success must be earned through strong stats, skills, or context. 
            - Unclear or marginal cases lean toward failure."""

# hard = death-march
def eval_action_hard():
    return """
    1.5 **Evaluation Rules (Souls-Like Death-March Difficulty)**:
        - Identify the action category (combat, social, exploration, technical, survival, etc.)
        - Determine relevant stats, skills, and context modifiers
        - Compare character capability vs. challenge difficulty
        - Emotional state, determination, or narrative flavor may color the description of outcomes, but they must never outweigh raw capability, stats, or chance when determining success or failure.
        - Apply death-march bias: success only if advantage is overwhelming AND risks are mitigated
        - If outcome is ambiguous, fail with consequence (damage, loss, escalation, worsening conditions)
        - If outcome is marginally justified, fail (the world exploits weakness)
        - Impossible actions (contradicting setting rules, physics, or resources) always fail catastrophically, often with collateral damage
        - Failure is rarely clean: it introduces new threats, worsens conditions, or escalates danger
        - Success is never free: it drains resources, inflicts scars, or sets up the next trial
        
        Souls-Like Death-March Baseline:
            - The world is actively hostile, indifferent to fairness, and punishes even small mistakes. 
            - Failure is the default. 
            - Success is possible only through mastery, preparation, and sacrifice. 
            - Every victory extracts a toll."""

# Tailor specific rulesets here
def eval_sheet():
    return """        
    1.6 **Evaluation Character Sheet Template**:
        Baseline:    
            - For every character involved in the action: Personalize a separate sheet using the template.
            - Adapt terminology to the setting.
            - The sheets must be normalized to resolve actions against each other.
            - The sheets always include, but are not limited to:
            
        **Sheet Template**:            
            Base Stats:
                - Health
                    - Physical integrity: Only altered by physical/medical/magical healing and harm.
                    - Regenerates very slowly through natural recovery.
                    - Tiers: ("unharmed", "scraped", "slightly injured", "injured", "heavily injured", "near death", "dead")
                - Stamina
                    - Resource for physical actions
                    - Regenerates quickly through natural recovery.
                    - Tiers: ("rested", "slightly exhausted", "exhausted", "heavily exhausted", "depleted")
                - Mana (generalized bucket for how Magic is fueled)
                    - Resource for magical actions
                    - Regenerates quickly through rest, meditation and the like, but slowly naturally.
                    - Tiers: ("full", "slightly spent", "half spent", "nearly spent", "spent", "None")
                    
            Character Stats:
                - Strength (physical power, carrying, melee damage)
                - Dexterity (agility, reflexes, ranged accuracy)
                - Constitution (endurance, toughness, resistance)
                - Intelligence (reasoning, knowledge, problem-solving)
                - Wisdom (perception, intuition, willpower)
                - Charisma (presence, persuasion, leadership)
    
            Skills (decide based on context, but always include common checks):
                - Perception (spotting hidden details, noticing danger)
                - Insight (reading intentions, emotional awareness)
                - Persuasion (convincing, negotiating, diplomacy)
                - Intimidation (coercion, threats, force of presence)
                - Deception (lying, disguises, trickery)
                - Stealth (moving quietly, avoiding detection)
                - Athletics (climbing, swimming, raw physical feats)
                - Survival (tracking, foraging, navigating wilderness)
                - Investigation (searching, analyzing, deducing clues)
                - Arcana/Occult (knowledge of magic or supernatural, if relevant)
                - Medicine (healing, stabilizing, treating wounds)
                - Crafting/Repair (building, fixing, improvising tools)
                - Technology/Engineering (setting appropriate)
                - Performance (acting, music, storytelling)
    
            Optional Contextual Skills:
                - Include only if the setting clearly supports them (e.g., Technology, Firearms, Streetwise, Animal Handling, Magic)
                - Omit if not relevant; do not invent without basis
    
            Combat Action Profile:
                - General combat style or affinity (melee, ranged, defensive, opportunistic, etc.)
                - Derived from context; note strengths and vulnerabilities
                
            Social Action Profile:
                - Seek advice from: Dr. Nguyen, a Harvard trained anthropologist.
            
            Equipment:
                - List only items explicitly given or logically inferable from context
                - List only immediately accessible items
                - Do not invent or embellish beyond what is supported
            
            Currency/Wealth:
                - Summarize general wealth level and infer the immediate access to these resources
            
            Status Effects:
                - Note any current conditions that alter performance (e.g., wounded, poisoned, exhausted, inspired)
                - Derive strictly from context; do not fabricate
                - Include both penalties and temporary advantages"""

"""
Do not edit below here
"""
def write_action_eval_bucket():
    """
    Writes evaluation data into the DB.
    Table: action_eval_bucket (id INTEGER PRIMARY KEY CHECK(id = 1), -- always 1, singleton row)
    """
    sheet = eval_sheet()
    easy = eval_action_easy()
    med = eval_action_med()
    hard = eval_action_hard()
    diff = get_difficulty()

    # Concatenate all text for token counting
    all_together = "\n".join([sheet, easy, med, hard, diff])
    tokencost = count_tokens(all_together)

    with write_connection() as conn:
        cursor = conn.cursor()
        sql = """
        INSERT INTO action_eval_bucket (
            id, eval_sheet, easy, medium, hard, difficulty, token_cost
        )
        VALUES (1, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            eval_sheet = excluded.eval_sheet,
            easy       = excluded.easy,
            medium     = excluded.medium,
            hard       = excluded.hard,
            difficulty = excluded.difficulty,
            token_cost = excluded.token_cost;
        """
        cursor.execute(sql, (sheet, easy, med, hard, diff, tokencost))