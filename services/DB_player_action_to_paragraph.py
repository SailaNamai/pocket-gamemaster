# services.DB_player_action_to_paragraph.py

from services.DB_token_cost import count_tokens
from services.DB_access_pipeline import write_connection

def player_action_to_paragraph(player_action: str) -> dict:
    """
    Inserts the player's action as a new paragraph in the database
    with story_id='continue_with_UserAction'. Returns the new row's
    id and content so the front end can wire up paragraph editing.
    """
    # Guard clause: reject None or empty/whitespace-only input
    if not player_action or not player_action.strip():
        return None

    token_cost = count_tokens(player_action)
    with write_connection() as conn:
        cursor = conn.cursor()

        story_id = 'continue_with_UserAction'

        # 1. Figure out the next paragraph_index for this story_id
        cursor.execute(
            "SELECT MAX(paragraph_index) FROM story_paragraphs WHERE story_id = ?",
            (story_id,)
        )
        max_index = cursor.fetchone()[0] or 0
        next_index = max_index + 1

        # 2. Insert the new paragraph
        cursor.execute(
            """
            INSERT INTO story_paragraphs
              (story_id, paragraph_index, content, token_cost)
            VALUES
              (?, ?, ?, ?)
            """,
            (story_id, next_index, player_action, token_cost)
        )

        # 3. Grab the newly created row's id & content
        new_id = cursor.lastrowid
        cursor.execute(
            "SELECT id, content, story_id FROM story_paragraphs WHERE id = ?",
            (new_id,)
        )
        row = cursor.fetchone()

        return {'id': row[0], 'content': row[1], 'story_id': row[2]}