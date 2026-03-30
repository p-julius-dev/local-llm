from flask import Flask, render_template, request, jsonify, Response
import sqlite3
from functions import process_user_message, create_new_session, get_all_sessions, load_session_messages, save_message
from datetime import datetime
import signal
import sys
import os
import pandas as pd
from ollama import chat

app = Flask(__name__)

# create upload folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#in memroy storage
loaded_files = {}

DB_PATH = "db/chat_sessions.db"

# Create database and tables at initial startup 
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            name TEXT
        )
    """)

    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        )
    """)

    conn.commit()
    conn.close()

# Call this on startup
init_db()

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
        {
            "session_id": s[0],
            "start_time": s[1],
            "name": s[2]   # ← THIS IS THE FIX
        }
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

# Start New session
@app.post("/new_session")
def new_session():
    global current_session_id
    global messages

    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        cursor = conn.cursor()
        # Create session: returns (id, name)
        current_session_id, default_name = create_new_session(cursor)
        conn.commit()

    messages = []

    # Send both ID and name back to frontend
    return jsonify({
        "status": "ok",
        "session_id": current_session_id,
        "name": default_name
    })

def safe_exit(sig, frame):
    """Handles Ctrl+C gracefully"""
    print("\n[INFO] Ctrl+C detected — shutting down server safely...")
    
    # Optional: do any final cleanup here
    # e.g., commit remaining messages, close DB if needed
    # If using 'with' blocks for DB, this is usually unnecessary
    
    sys.exit(0)  # exit Python cleanly

# delete session
@app.post("/delete_session/<session_id>")
def delete_session(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Delete messages first (foreign key dependency)
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

        conn.commit()

    return jsonify({"status": "ok"})

# CSV file upload helper 3/30
def load_csv(filepath):
    df = pd.read_csv(filepath)
    return df

# ------------------------
# Routes
# ------------------------

@app.get("/")
def index():
    """Render chat UI"""
    return render_template("index.html")


@app.post("/chat")
def chat_route():
    global current_session_id
    global messages

    user_message = request.json.get("message", "")

    def generate():
        global current_session_id   # REQUIRED HERE

        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
            cursor = conn.cursor()

            if current_session_id is None:
                current_session_id, _ = create_new_session(cursor)

            messages.append({"role": "user", "content": user_message})
            save_message(cursor, current_session_id, "user", user_message)

            stream = chat(
                model="phi3:mini",
                messages=messages,
                options={"temperature": 0.4},
                stream=True
            )

            assistant_reply = ""

            for chunk in stream:
                if "message" in chunk:
                    content = chunk["message"]["content"]
                    assistant_reply += content
                    yield content

            messages.append({"role": "assistant", "content": assistant_reply})
            save_message(cursor, current_session_id, "assistant", assistant_reply)
            conn.commit()

    return Response(generate(), content_type="text/plain")

# rename session
@app.route("/rename_session/<int:session_id>", methods=["POST"])
def rename_session(session_id):
    new_name = request.json.get("name", "").strip()
    if not new_name:
        return {"status": "error", "message": "Name cannot be empty"}, 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET name = ? WHERE session_id = ?", (new_name, session_id))
    conn.commit()
    conn.close()

    return {"status": "ok", "name": new_name}

# upload endpoint backend 3/30
@app.post("/upload_csv")
def upload_csv():
    file = request.files.get("file")

    if not file:
        return {"status": "error", "message": "No file uploaded"}, 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)

    file.save(filepath)

    df = load_csv(filepath)
    loaded_files[file.filename] = df

    print(f"[DEBUG] Uploaded file saved to: {filepath}")
    print(f"[DEBUG] Loaded into memory: {file.filename} ({len(df)} rows)")

    return {"status": "ok", "filename": file.filename}

#TEMPROARY test route
@app.get("/upload_test")
def upload_test():
    return '''
    <h3>Upload CSV Test</h3>
    <form action="/upload_csv" method="post" enctype="multipart/form-data">
        <input type="file" name="file">
        <input type="submit">
    </form>
    '''


if __name__ == "__main__":
    try:
        print("[INFO] Starting Flask server. Press Ctrl+C to stop safely.")
        app.run(debug=True)
    finally:
        print("\n[INFO] Flask server stopped safely.")
        # Optional: any final cleanup here
