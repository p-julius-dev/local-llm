from flask import Flask, render_template, request, jsonify
import sqlite3
from functions import process_user_message, create_new_session, get_all_sessions, load_session_messages  # your refactored function
from datetime import datetime
import signal
import sys

app = Flask(__name__)

DB_PATH = "db/chat_sessions.db"

# Single active session for UI (can expand later)
current_session_id = None
messages = []

# Get all sessions
@app.get("/sessions")
def get_sessions():
    """Return all chat sessions for sidebar"""
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        cursor = conn.cursor()
        sessions = get_all_sessions(cursor)

    results = [
        {"session_id": s[0], "start_time": s[1]}
        for s in sessions
    ]

    return jsonify(results)

# Load messages for session
@app.get("/session/<session_id>")
def load_session(session_id):
    """Load messages for a selected session"""
    global messages
    global current_session_id 
    current_session_id = session_id

    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        cursor = conn.cursor()

        messages = load_session_messages(cursor, session_id)

    current_session = session_id

    return jsonify(messages)


def safe_exit(sig, frame):
    """Handles Ctrl+C gracefully"""
    print("\n[INFO] Ctrl+C detected — shutting down server safely...")
    
    # Optional: do any final cleanup here
    # e.g., commit remaining messages, close DB if needed
    # If using 'with' blocks for DB, this is usually unnecessary
    
    sys.exit(0)  # exit Python cleanly

# ------------------------
# Routes
# ------------------------

@app.get("/")
def index():
    """Render chat UI"""
    return render_template("index.html")


@app.post("/chat")
def chat_route():
    global messages
    global current_session_id

    user_message = request.json.get("message", "")

    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        cursor = conn.cursor()

        # Create session if it doesn't exist yet
        if current_session_id is None:
            current_session_id, _ = create_new_session(cursor)

        reply = process_user_message(cursor, current_session_id, messages, user_message)

        conn.commit()

    return jsonify({"reply": reply})

if __name__ == "__main__":
    try:
        print("[INFO] Starting Flask server. Press Ctrl+C to stop safely.")
        app.run(debug=True)
    finally:
        print("\n[INFO] Flask server stopped safely.")
        # Optional: any final cleanup here
