# services/story_force.py

def handle_forced_prompted_action(request_data, player_action):
    action = request_data.get("action", "")
    outcome = f"Result of action '{action}'"
    return {"result": outcome}
