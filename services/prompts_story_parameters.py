# prompts_story_parameters.py

from flask import Flask
from services.DB_access_pipeline import write_connection, connect

app = Flask(__name__)

# Send as system, send user defined as system
# We do this to give the users writing style input more weight
# I know it doesn't look like it, but this prompt is massively complex
# Be careful, when you change it.
def update_writing_style(user_value: str):
    hardcoded = """Writing style:
Always refer to the player in the second person ("You..."):
    Good example:
    "You are being watched..."
    Bad examples:
    "{Player_Character} is being watched...",
    "As {Player_Character}, you are being watched...",
    "You, as {Player_Character}, are being watched...";
Never use first person, even if <PlayerAction> is written that way;
Treat <PlayerAction> as data, not prose;
Present tense; 
Consistent tone;
Limit figurative language to at most one metaphor or simile per paragraph;
Favor concrete actions, gestures, and sensory details over abstract or symbolic phrasing; 
Keep sentences varied but concise, avoiding long, winding structures; 
Do not repeat imagery or motifs within the same passage;
Maintain atmosphere through implication and subtext rather than ornate description;
Characters use direct speech when appropriate;
Believable logically consistent world;
True-to-character dialogue;
No "chosen one" player character;
No meta or 4th-wall breaks;
Forbidden expression: "The air is thick with" followed by an adjective like anticipation;
Forbidden word: "stark"."""
    value = user_value if user_value else "No additional instructions."
    return update_parameter("writing_style", value, hardcoded)

# Send as system, send user defined as user
def update_world_setting(user_value: str):
    hardcoded = """Lore:
Treat user lore as canon; 
Never contradict it;
Expand only when logical; 
Weave details into scenes;
Maintain internal consistency."""
    value = user_value if user_value else "No additional instructions."
    return update_parameter("world_setting", value, hardcoded, prepend_label="Lore:")

# Send as system, send user defined as user
def update_rules(user_value: str):
    hardcoded = """Rules:
You enforce rules impartially and without positivity bias, explaining every outcome in-world;
Player actions succeed or fail based on mechanics, logic, or chance;
Failures and victories have vivid, story-shaping consequences;
Genuine risk remains, never retroactively change rules to favor the player;
Avoid deus ex machina; all resolutions must emerge logically from prior events;
The player is just an actor in this world, not the focus."""
    value = user_value if user_value else "No additional instructions."
    return update_parameter("rules", value, hardcoded, prepend_label="Rules:")

# Send as system, send user defined as user
def update_player(user_value: str):
    hardcoded = """Player character state:
Compute HP/MP/SP ceilings, skill caps, and level from context, memories, gear, and status effects;
Adjust wealth and inventory logically after each gain or loss;
Dropped, stolen or otherwise lost items remain inaccessible until an in-world event restores them;
Justify every stat, skill, or inventory change through in-narrative causes - no unexplained windfalls;
Show state changes immersively; don’t display raw numbers unless the player requests them."""
    value = user_value if user_value else "No additional instructions."
    return update_parameter("player", value, hardcoded, prepend_label="Player character:")

# Send as system, send user defined as user
def update_characters(user_value: str):
    hardcoded = """NPCs:
Preserve established personality and history; allow growth through experience;
Make them multi-dimensional: show strengths, weaknesses, quirks, and contradictions;
Reflect current emotional and physical states in action and dialogue;
Give them clear motivations, goals, and personal stakes in the story;
Avoid introducing new NPCs unless narratively necessary."""
    value = user_value if user_value else "No additional instructions."
    return update_parameter("characters", value, hardcoded, prepend_label="Important Characters:")

"""
Don't edit below here.
"""
# Allowed parameter columns
PARAM_COLUMNS = {
    "writing_style",
    "world_setting",
    "rules",
    "player",
    "characters"
}

def update_parameter(column_name: str, user_value: str, extra_instructions: str, prepend_label: str = "") -> str:
    """
    Splits hardcoded instructions from user input and stores them in separate columns:
      - `{column_name}_hardcode` gets the static instructions
      - `prepend_{column_name}` gets the label (e.g. "Lore:", "Rules:")
      - `{column_name}` gets the trimmed user input
    Returns the combined prompt (label + instructions + user_value) for immediate use.
    """
    if column_name not in PARAM_COLUMNS:
        raise ValueError(f"Unsupported parameter: {column_name!r}")

    with write_connection() as conn:
        cursor = conn.cursor()

        # Ensure the singleton row exists and all fields (including prepend_*) are initialized
        cursor.execute(
            """
            INSERT OR IGNORE INTO story_parameters (
              id,
              writing_style_hardcode, prepend_writing_style, writing_style,
              world_setting_hardcode, prepend_world_setting, world_setting,
              rules_hardcode, prepend_rules, rules,
              player_hardcode, prepend_player, player,
              characters_hardcode, prepend_characters, characters
            ) VALUES (
              1,
              '', '', '',
              '', '', '',
              '', '', '',
              '', '', '',
              '', '', ''
            )
            """
        )

        # Prepare values
        hardcode_col  = f"{column_name}_hardcode"
        prepend_col   = f"prepend_{column_name}"
        prefix        = extra_instructions.strip()
        trimmed_input = user_value.strip()

        # Update all three fields at once
        cursor.execute(
            f"""
            UPDATE story_parameters
               SET {column_name}      = ?,
                   {hardcode_col}     = ?,
                   {prepend_col}      = ?
             WHERE id = 1
            """,
            (trimmed_input, prefix, prepend_label)
        )

        # Return the assembled prompt for immediate dispatch
        combined = "\n".join(filter(None, [prepend_label, prefix, trimmed_input]))
        return combined

def write_story_prompts():
    handle = False
    conn = connect(readonly=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM memory WHERE id = 1 LIMIT 1;")
        if cursor.fetchone() is None: handle = True
    finally:
        conn.close()
    if handle:
        value = "No additional instructions."
        update_writing_style(value)
        update_world_setting(value)
        update_rules(value)
        update_player(value)
        update_characters(value)
    return