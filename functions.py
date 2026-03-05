import uuid
from datetime import datetime

# ------------------------
# Helper Functions
# ------------------------

def generate_new_session_id():
    return str(uuid.uuid4())


def get_all_sessions(cursor):
    cursor.execute("""
        SELECT session_id, start_time
        FROM sessions
        ORDER BY start_time DESC
    """)
    return cursor.fetchall()


def load_session_messages(cursor, session_id):
    cursor.execute("""
        SELECT role, content
        FROM messages
        WHERE session_id = ?
        ORDER BY timestamp ASC
    """, (session_id,))
    rows = cursor.fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]


def create_new_session(cursor):
    """Create a new session and insert into DB."""
    session_id = generate_new_session_id()
    start_time = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO sessions (session_id, start_time) VALUES (?, ?)",
        (session_id, start_time)
    )
    return session_id, start_time


def save_message(cursor, session_id, role, content):
    """Save a message to the DB."""
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.now().isoformat())
    )