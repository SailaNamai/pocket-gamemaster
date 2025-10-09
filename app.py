# app.py
"""
System
"""
from flask import Flask, render_template, request, jsonify, make_response
import sqlite3
import logging

"""
Token budget
"""
from services.llm_config import GlobalVars
from services.llm_config_helper import get_n_ctx, get_recent, get_mid, get_long
from services.DB_token_budget import write_budget, check_sanity
"""
# Prompt Assembly (Initial DB and UserInput)
"""
from services.DB_access_pipeline import write_connection, connect
from services.prompts_story_parameters import update_writing_style, update_world_setting, update_rules, update_player, update_characters
from services.prompts_system import write_system_prompts
from services.prompts_story_parameters import write_story_prompts
from services.prompts_memory_prefix import write_memory_prefix
from services.prompts_tag import write_tagging_prompts
from services.DB_token_budget import write_initial_budget, update_budget
from services.prompts_eval_action import write_action_eval_bucket
from services.DB_difficulty import write_difficulty, get_difficulty
"""
Buttons (Continue = continue_story & player_action, ...)
"""
from services.DB_persist_user_edit import persist_user_edit
from services.story_new import generate_story_new
from services.story_continue import generate_story_continue
from services.DB_player_action_to_paragraph import player_action_to_paragraph
from services.story_player_action import generate_player_action
from services.story_player_action_eval import evaluate_player_action
#from services.story_force import handle_forced_prompted_action
"""
Memories&Summaries
"""
from services.prompts_summarize_from_player_action import write_mid_memory_prompts
from services.summarize_pipeline import summarize
from services.DB_summarize_publish import publish_long_memory, publish_mid_memory

# app.py
app = Flask(__name__)

SCHEMA_SQL = GlobalVars.SCHEMA
def init_db():
    with write_connection() as conn:
        with open(SCHEMA_SQL, 'r') as f:
            conn.executescript(f.read())

# This sends all INFO+ logs (from all modules) to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s"
)

# Serve the front-end
@app.route('/')
def index():
    resp = make_response(render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

"""
Endpoint for front-end listener (story parameters)
On new entry we write to DB (if block), update token budget and return "ok".
"""
@app.route('/update_story_parameter', methods=['POST'])
def update_story_parameter():
    data = request.get_json()
    param = data.get("parameter")
    value = data.get("value", "")

    if param == "writing_style":
        update_writing_style(value)
    elif param == "world_setting":
        update_world_setting(value)
    elif param == "rules":
        update_rules(value)
    elif param == "player":
        update_player(value)
    elif param == "characters":
        update_characters(value)
    else:
        return jsonify({"error": "Unknown parameter"}), 400

    update_budget()

    return jsonify({"status": "ok"})

"""
Load story parameters (def initial state) from DB on first/new front end visit.
Then load the story (def story_history).
"""
@app.route('/api/initial_state')
def initial_state():
    conn = connect(readonly=True)
    try:
        cur  = conn.cursor()
        # fetch story params
        cur.execute("SELECT writing_style, world_setting, rules, player, characters FROM story_parameters WHERE id=1")
        sp = cur.fetchone() or ['', '', '', '', '']
    finally:
        conn.close()

    return jsonify({
      "story_parameters": {
        "writing_style": sp[0],
        "world_setting": sp[1],
        "rules": sp[2],
        "player": sp[3],
        "characters": sp[4]
      },
      "memory": {
        "mid_memory": publish_mid_memory(),
        "long_memory": publish_long_memory()
      },
      "budget": {
          "n_ctx": get_n_ctx(),
          "recent": get_recent(),
          "mid": get_mid(),
          "long": get_long()
      },
      "difficulty": {
          "diff_setting": get_difficulty(),
      }
    })
# Load story from DB on first visit
@app.route('/api/story_history')
def story_history():
    conn = connect(readonly=True)
    try:
        conn.row_factory = sqlite3.Row
        cur  = conn.cursor()

        cur.execute("""
          SELECT id, content, story_id
            FROM story_paragraphs
        ORDER BY id
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    paragraphs = [
      { "id":    row["id"],
        "content": row["content"],
        "story_id": row["story_id"] }
      for row in rows
    ]
    return jsonify({ "paragraphs": paragraphs })

"""
Generation pipelines:
"""
# New is, when the Continue button is pressed and there is no story.
@app.route('/api/new', methods=['POST'])
def api_new():
    new_paragraph = generate_story_new()
    return jsonify({
        'story': new_paragraph,
        'mid_memory': publish_mid_memory(),
        'long_memory': publish_long_memory()
    })

# Continue is, when there is story and we continue without a UserAction entered
@app.route('/api/continue', methods=['POST'])
def api_continue():
    data = request.get_json() or {}
    update_db = data.get('candidate')
    if update_db: persist_user_edit(update_db)
    new_paragraph = generate_story_continue()
    return jsonify({
        'story': new_paragraph,
        'mid_memory': publish_mid_memory(),
        'long_memory': publish_long_memory()
    })

# Player_action is, when the user has entered an action
# api_new (no story) takes precedence and ignores the user action
@app.route('/api/player_action', methods=['POST'])
def api_player_action():
    data = request.get_json() or {}
    update_db = data.get('candidate')
    if update_db: persist_user_edit(update_db)
    player_action = data.get('action', '')
    action_row = player_action_to_paragraph(player_action) # Save the returned player_action to DB {id, content, story_id}
    evaluate_player_action() # evaluation/outcome of that action, writes directly into db
    llm_row = generate_player_action() # handle_player_action() must also return a dict {id, content, story_id}
    mid_html = publish_mid_memory()
    long_html = publish_long_memory()
    # return both rows as an array
    paragraphs = []
    if action_row: paragraphs.append(action_row)
    if llm_row:   paragraphs.append(llm_row)
    return jsonify({
        'paragraphs': paragraphs,
        'mid_memory': mid_html,
        'long_memory': long_html
    })

"""
Memory pipeline:
"""
# Summarize is run after the newest generation has been published.
@app.route('/api/summarize', methods=['POST'])
def api_summarize():
    summarize()
    return "backend_done"

"""
Budget:
"""
# update_budget is run when the user gives token budgeting parameters
@app.route('/api/update_budget', methods=['POST'])
def api_update_budget():
    data = request.get_json(force=True) or {}

    n_ctx = data.get('n_ctx')
    recent = data.get('recent')
    mid = data.get('mid')
    long_ = data.get('long')

    # convert and validate here or rely on check_sanity doing it
    if not check_sanity(n_ctx, recent, mid, long_):
        return jsonify(message='insane_request'), 400

    write_budget(int(n_ctx), int(recent), int(mid), int(long_))
    return jsonify(message='update_successful'), 200

# difficulty settings app-route
@app.route('/api/update_difficulty', methods=['POST'])
def api_update_difficulty():
    data = request.get_json() or {}

    # pass difficulty and write to DB
    difficulty = data.get('difficulty')
    write_difficulty(difficulty)

    return jsonify(message='update_successful'), 200

# This stuff here runs once everytime you do python app.py
if __name__ == '__main__':
    init_db()
    # Fill DB with hard coded stuff and placeholders
    write_system_prompts()
    write_story_prompts()
    write_memory_prefix()
    write_tagging_prompts()
    write_mid_memory_prompts()
    write_initial_budget()
    write_action_eval_bucket()
    # You can remove debug=True or set it to False. True will restart the app when the code changes (but not write to DB).
    # app.run(debug=True, port=5000, host='0.0.0.0', threaded=True) makes the app accessible from the local network: remove to limit to local machine only.
    # app.run(debug=True, port=5000, threaded=True) removes local network access.
    # Change port if you need to.
    # Don't think we actually need threaded=True
    app.run(debug=True, port=5000, threaded=True)



"""
# I don't think I'll actually implement this.
# Force is, when the player enters an action and clicks the 'Force' button (Intended as a kind of SuperUser prompt - WIP).
@app.route('/api/force', methods=['POST'])
def api_force():
    new_paragraph = "Empty"
    return jsonify({
        'story': new_paragraph,
        'mid_memory': publish_mid_memory(),
        'long_memory': publish_long_memory()
    })
"""

# Create once at app startup
# Found a better solution, I think.
#from concurrent.futures import ThreadPoolExecutor
#executor = ThreadPoolExecutor(max_workers=2)