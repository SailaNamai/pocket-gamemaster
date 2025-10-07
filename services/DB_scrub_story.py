# services.DB_scrub_story.py

from services.DB_access_pipeline import write_connection

def clear_story_tables():
    with write_connection() as conn:
        # 1) Wipe out all story paragraphs
        conn.execute("DELETE FROM story_paragraphs;")
        # 2) Reset the AUTOINCREMENT counter for story_paragraphs
        conn.execute(
            "DELETE FROM sqlite_sequence WHERE name = ?;",
            ("story_paragraphs",)
        )
