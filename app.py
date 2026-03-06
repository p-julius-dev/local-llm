from flask import Flask, render_template, request, jsonify
import sqlite3
from functions import process_user_message  # your refactored function
from datetime import datetime
import signal
import sys

app = Flask(__name__)

DB_PATH = "db/chat_sessions.db"

def safe_exit(sig, frame):
    """Handles Ctrl+C gracefully"""
    print("\n[INFO] Ctrl+C detected — shutting down server safely...")
    
    # Optional: do any final cleanup here
    # e.g., commit remaining messages, close DB if needed
    # If using 'with' blocks for DB, this is usually unnecessary
    
    sys.exit(0)  # exit Python cleanly

# Single active session for UI (we can expand later)
session_id = "ui-session"
messages = []

# ------------------------
# Routes
# ------------------------

@app.get("/")
def index():
    """Render chat UI"""
    return render_template("index.html")


@app.post("/chat")
def chat_route():
    """Receive message, process with LLM, return reply"""
    global messages
    user_message = request.json.get("message", "")

    # Use a short-lived DB connection with check_same_thread=False
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        cursor = conn.cursor()

        # Call your backend function to process the message
        reply = process_user_message(cursor, session_id, messages, user_message)

        # Commit changes (optional; 'with' usually commits automatically on close)
        conn.commit()

    # Return the assistant's reply as JSON
    return jsonify({"reply": reply})

if __name__ == "__main__":
    try:
        print("[INFO] Starting Flask server. Press Ctrl+C to stop safely.")
        app.run(debug=True)
    finally:
        print("\n[INFO] Flask server stopped safely.")
        # Optional: any final cleanup here
