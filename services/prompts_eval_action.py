# services.prompts_eval_action.py

from services.DB_token_cost import count_tokens
from services.DB_access_pipeline import write_connection

# meant to eventually select the front-end provided difficulty setting
def get_eval_action_difficulty():
    return "Placeholder"

# We galaxy-brain cheat easy=medium, medium=hard, hard=souls like death-march
def eval_action_easy():
    return """Evaluation Rules (Medium Difficulty):
This is the medium baseline: outcomes should balance fairness and challenge. 
Characters succeed when their abilities or context clearly justify it, but 
uncertain or marginal cases lean toward failure. Medium bias assumes the 
world resists easy victories but rewards strong advantages.

- Identify the action category (combat, social, exploration, technical, etc.)
- Determine relevant stats, skills, and context modifiers
- Compare character capability vs. challenge difficulty
- Apply medium bias: success requires clear advantage or strong justification
- If outcome is ambiguous or unsupported, default to failure
- Impossible actions (those that contradict established setting rules, physical laws, or available resources) always fail"""

# default
def eval_action_med():
    return """Evaluation Rules (Hard Difficulty):
This is the hard baseline: outcomes favor failure unless the character has overwhelming advantage. 
The world is harsh and resistant; success must be earned through strong stats, skills, or context. 
Unclear or marginal cases lean toward failure.

- Identify the action category (combat, social, exploration, technical, etc.)
- Determine relevant stats, skills, and context modifiers
- Compare character capability vs. challenge difficulty
- Emotional state, determination, or narrative flavor may color the description of outcomes, but they must never outweigh raw capability, stats, or chance when determining success or failure.
- Apply hard bias: success only if advantage is decisive or overwhelming
- Partial successes or failures extract an appropriate cost
- If outcome is ambiguous, unsupported, or only marginally justified, fail
- Impossible actions (those that contradict established setting rules, physical laws, or available resources) always fail"""

def eval_action_hard():
    return """Evaluation Rules (Souls-Like Death-March Difficulty):
This is the cruel baseline: the world is actively hostile, indifferent to fairness, and punishes even small mistakes. 
Failure is the default. Success is possible only through mastery, preparation, and sacrifice. 
Every victory extracts a toll.

- Identify the action category (combat, social, exploration, technical, survival, etc.)
- Determine relevant stats, skills, and context modifiers
- Compare character capability vs. challenge difficulty
- Emotional state, determination, or narrative flavor may color the description of outcomes, but they must never outweigh raw capability, stats, or chance when determining success or failure.
- Apply death-march bias: success only if advantage is overwhelming AND risks are mitigated
- If outcome is ambiguous, fail with consequence (damage, loss, escalation, worsening conditions)
- If outcome is marginally justified, fail (the world exploits weakness)
- Impossible actions (contradicting setting rules, physics, or resources) always fail catastrophically, often with collateral damage
- Failure is rarely clean: it introduces new threats, worsens conditions, or escalates danger
- Success is never free: it drains resources, inflicts scars, or sets up the next trial"""

def eval_sheet():
    return """
- For every character involved in the action, personalize a complete sheet using the template
- Adapt terminology to the setting and ensure all sections are filled
- Keep the sheet concise but functional for resolving actions
- The sheet always includes, but is not limited to:

Base Stats:
- Health
- Stamina
- Mana (generalized bucket for how Magic is "fueled")

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

Combat Profile:
- General combat style or affinity (melee, ranged, defensive, opportunistic, etc.)
- Derived from context; note strengths and vulnerabilities

Equipment:
- List only items explicitly given or logically inferable from context
- List only immediately accessible items
- Do not invent or embellish beyond what is supported

Currency/Wealth:
- Summarize general wealth level and immediate access to resources

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
    diff = get_eval_action_difficulty()

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
        conn.commit()

"""
Difficulty outtakes
"""

"""Evaluation Rules (Easy Difficulty):
This is the easy baseline: outcomes favor the character unless there is a strong reason to fail. 
Characters succeed in most reasonable attempts, and the world is permissive of effort. 
Unclear or marginal cases lean toward success.

- Identify the action category (combat, social, exploration, technical, etc.)
- Determine relevant stats, skills, and context modifiers
- Compare character capability vs. challenge difficulty
- Apply easy bias: success is granted if there is any plausible justification
- If outcome is highly implausible or explicitly contradicted, then fail
- Impossible actions (those that contradict established setting rules, physical laws, or available resources) always fail"""