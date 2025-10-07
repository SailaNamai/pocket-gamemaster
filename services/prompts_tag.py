# services.prompts_tag.py

from services.DB_access_pipeline import write_connection

def get_tagging_style():
    return """
    Output a single valid JSON object that exactly matches this schema and nothing else:

    - The JSON object must contain exactly five keys: "location", "character", "importance", "emotion", "state".
    - Each value must be a string.
    - The "character", "emotion" and "state" value may each list multiples; if there are multiple, separate them with a semicolon and a space (e.g., "Aethera; Thrain").
    - The "importance" value must be exactly one of: "Very High", "High", "Medium", "Low", "Very Low".
    - The "location" value must be a concise but specific proper‑noun style name. 
    - Do not add extra keys, comments, or any trailing text. Emit exactly one JSON object (no surrounding text, no code fences).
    
    Importance Levels:
    
    - Very High: Major narrative climaxes like marriage, deaths of important NPCs, finished story arcs...
    - High: Events that directly advance the narrative or alter key relationships
    - Medium: Progress in side narratives and changes in inventory or resources
    - Low: Symbolism and minor details.
    - Very Low: Purely descriptive or flavor text
    
    Tag Naming Style:
    
    - "location": Concise but specific proper‑noun style name. 
      a) Always prefer the unique given name if available (e.g., "The Dancing Elephant"). 
      b) If no unique name is given, use a short descriptive compound (e.g., "Desert Tavern", "Northern Forest") 
      rather than a generic term like "Tavern" or "Forest". 
      c) If no unique or generic term is given, fall back to unknown. (e.g., "Unknown Tavern", "Unknown Forest")
    - "character": List one or more character names exactly as they appear in the story. 
      If multiple, separate them with "; " (semicolon + space).
    - "emotion": One or more emotions, separated by "; ". Each must be a single lowercase word (e.g., "fear; hope; relief").
    - "state": One or more short verb phrases describing the current activity or condition. 
      a) If multiple, separate them with "; " (semicolon + space) (e.g., "searching for supplies; seeking shelter", "resting; preparing for battle").
      b) If the state is the same, use a separate value for each item  (e.g., "buying supplies; buying map")

    Examples of the required format:
    
    Good examples:
    
    Summary: I step inside the ransacked home of Mrs. Jenkins and find shelter from the howling wind outside, 
    casting flickering shadows with my candle light amidst broken furniture and scattered belongings. 
    I rummage through debris to gather supplies: a nearly full can of beans, a first-aid kit, an old 
    flashlight still working well enough for now, a cookbook for potential recipes or ideas, Mrs. Jenkins' 
    trusty revolver that's been dusted off but still functional - its reassuring sound when racked 
    gives me hope it might be useful in the future. In the kitchen I find stale crackers, almost-empty 
    sugar bag and a rusted can opener along with 'North' written on the wall possibly left by my parents 
    as a clue to follow. Upstairs, amidst Mrs. Jenkins' bedroom chaos, I discover her pocket knife still 
    serviceable despite being rusty from disuse - it's clear someone searched through her belongings here 
    too but what they were looking for remains unclear.

    Output: {"location": "Mrs. Jenkins' Home", "character": "Narrator", "importance": "Medium", "emotion": "curiosity; anxiety; hopefulness", "state": "scavenging for supplies"}
    
    Summary: As I creep closer to the abandoned house, my eyes fixed on the candlelight within, memories of 
    the relentless horde from before flood back into my mind. I use an oak tree for cover and peer up at a grimy 
    window where two figures huddle together in tense conversation. The old man stands up and moves out of sight 
    while the woman's gaze drifts off into thought, lost in the darkness as if searching for something beyond 
    those boarded-up windows - perhaps even my parents? This couple could hold some key to understanding what 
    happened to everyone else and where my parents went. I weigh the risks of approaching them against staying 
    outside in the cold with those shambling creatures roaming around, ultimately deciding that it's worth a try to 
    find out if they might offer hope or guidance amidst this shattered world.
    
    Output: {"location": "Abandoned House", "character": "Narrator; Old Man; Woman", "importance": "High", "emotion": "fear; curiosity; hope", "state": "approaching cautiously; assessing risk"}
    
    Summary: As I unpack my meager supplies on their table near the fireplace, Jed and Emily watch with interest, 
    revealing their own scarcity by eyeing our offerings appreciatively. We share Mrs. Jenkins' revolver, 
    can of beans, first-aid kit, flashlight, cookbook, and rations; they accept the sharing gesture warmly. 
    The intimacy is palpable as we bond over shared stories: Jed admires the gun's potential usefulness and 
    Emily reminisces about her mother using a similar cookbook in happier times. This moment underscores the 
    significance of small comforts amidst chaos and hardship, fostering an unspoken understanding that human 
    connection can be our greatest sustenance.
    
    Output: {"location": "Jed's Cottage", "character": "Hans; Jed; Emily", "importance": "Medium", "emotion": "gratitude; longing; hopefulness", "state": "sharing food; sharing supplies"}
    
    Bad examples and why they fail:
    
    1) Invalid JSON (missing quotes, commas or braces)
    {location: Tavern, character: Aethera; Thrain, importance: High, emotion: curiosity, state: researching}  
    - Fails because keys and string values must be quoted and JSON must be syntactically valid.
    
    2) Missing or extra keys
    {"location": "Tavern", "character": "Aethera", "importance": "Low", "emotion": "curiosity"}  
    — Fails because it is missing the "state" key.
    
    {"location": "Tavern", "character": "Aethera", "importance": "High", "emotion": "curiosity", "state": "researching", "mood": "excited"}  
    — Fails because it includes an extra "mood" key.
    
    3) Incorrect importance value
    {"location": "Tavern", "character": "Aethera", "importance": "high", "emotion": "curiosity", "state": "researching"}  
    — Fails because "importance" must be exactly "Very High", "High", "Medium", "Low" or "Very Low" (case-sensitive).
    
    4) Non-string types or arrays instead of semicolon-delimited string
    {"location": "Tavern", "character": ["Aethera","Thrain"], "importance": "Medium", "emotion": "curiosity", "state": "researching"}  
    — Fails because "character" must be a single string; multiple entries must be in one string separated by "; ".
    
    5) Empty value or missing value
    {"location": "Tavern", "character": "", "importance": "High", "emotion": "curiosity", "state": "researching"}  
    — Fails because values must be non-empty strings.
    """

def write_tagging_prompts():
    # get prompt
    entry = get_tagging_style()

    # Open connection and upsert
    with write_connection() as conn:
        cursor = conn.cursor()
        sql = """
        INSERT INTO mid_memory_bucket (id, tagging_hardcode)
        VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET
            tagging_hardcode = excluded.tagging_hardcode;
        """
        cursor.execute(sql, (entry,))