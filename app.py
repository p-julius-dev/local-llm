from flask import Flask, render_template, request, jsonify, Response
import sqlite3
from functions import process_user_message, create_new_session, get_all_sessions, load_session_messages, save_message, filter_dataset,execute_tool
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

# Single active session for UI 
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
            "name": s[2]   
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

# CSV file upload helper 
def load_csv(filepath):
    df = pd.read_csv(filepath)
    return df

#CSV File reader helper 
def get_dataset_info(df):
    return {
        "columns": list(df.columns),
        "rows": len(df),
        "preview": df.head(5).to_dict(orient="records")
    }

# List files endpoint
@app.get("/files")
def list_files():
    return {
        "status": "ok",
        "files": list(loaded_files.keys())
    }

# Filter dataset endpoint - CHANGED from @app.get("/filter") 4/18
@app.get("/filter_dataset")
def filter_data():
    filename = request.args.get("file")
    column = request.args.get("column")
    value = request.args.get("value")

    df = loaded_files.get(filename)

    if df is None:
        return {"status": "error", "message": "File not loaded"}, 404

    if column not in df.columns:
        return {"status": "error", "message": "Invalid column"}, 400

    try:
        result_df = filter_dataset(df, column, value)
        
        #return {
            #"status": "ok",
            #"rows": len(result_df),
            #"preview": result_df.head(5).to_dict(orient="records")
        #}
        return {
            "status": "ok",
            "columns": list(result_df.columns),
            "row_count": len(result_df),
            "preview": result_df.head(10).to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
    
#keep old /filter functional 4/18 it doesn't do row counts, leaving it as-is
@app.get("/filter")
def filter_data_legacy():
    return filter_data()

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
    
    session_id = current_session_id #chat freeze fix 4/19

    #new generate session to fix db freeze 4/19
    def generate(session_id): 

    # --- 1. SAVE USER MESSAGE (DB OPEN SHORT TIME) ---
        with sqlite3.connect(DB_PATH, timeout=5) as conn:
            cursor = conn.cursor()

            if session_id is None:
                session_id, _ = create_new_session(cursor)

            messages.append({"role": "user", "content": user_message})
            save_message(cursor, session_id, "user", user_message)
            conn.commit()
        
        # -- tool suggestion system instruction 4/19 --#

        system_prompt = {
            "role": "system",
            "content": """
        You are a tool-calling system.

        You MUST follow these rules:

        1. If the user request involves dataset operations, respond ONLY with valid JSON.
        2. Output must contain ONLY JSON. No explanations. No extra text. No markdown.
        3. The JSON must follow this format exactly:

        {
        "action": "filter_dataset",
        "parameters": {
            "file": "<filename>",
            "column": "<column_name>",
            "value": "<value>"
        }
        }

        4. Do NOT invent new files.
        5. Do NOT explain your answer.
        6. Do NOT repeat the request.
        7. If you are unsure, still output JSON using best guess.
        8. You are NOT allowed to describe results or outcomes.
        9. You are NOT allowed to assume what the system will return.
        10. You ONLY output the action request JSON.

        Violation = invalid output.
        """
        }

        # --- 2. STREAM LLM (NO DB CONNECTION) ---
        stream = chat(
            model="phi3:mini",
            messages=[system_prompt] + messages,
            options={"temperature": 0.4},
            stream=True
        )

        assistant_reply = ""

        for chunk in stream:
            if "message" in chunk:
                content = chunk["message"]["content"]
                assistant_reply += content
                yield content
        
        #tool handling added 4/19
        import json
        import re

        tool_action = None

        # grab first JSON block only
        match = re.search(r"\{[\s\S]*?\}", assistant_reply)

        if match:
            raw = match.group(0)

            try:
                tool_action = json.loads(raw)
            except:
                tool_action = None

        if tool_action and "action" in tool_action:
            print("[DEBUG] Tool suggested:", tool_action)

        # --- 3. SAVE ASSISTANT MESSAGE (DB OPEN SHORT TIME) ---
        with sqlite3.connect(DB_PATH, timeout=5) as conn:
            cursor = conn.cursor()

            messages.append({"role": "assistant", "content": assistant_reply})
            save_message(cursor, session_id, "assistant", assistant_reply)
            conn.commit()

    return Response(generate(session_id), content_type="text/plain") #added session_id 4/19

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

# upload endpoint backend 
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

# upload CSV routing 
@app.get("/dataset_info/<filename>")
def dataset_info(filename):
    df = loaded_files.get(filename)

    if df is None:
        return {"status": "error", "message": "File not loaded"}, 404

    return {
        "status": "ok",
        "data": get_dataset_info(df)
    }
#Debug Endpoint 4/18
@app.post("/run_tool")
def run_tool():
    data = request.json
    action = data.get("action")
    parameters = data.get("parameters", {})

    try:
        result = execute_tool(action, parameters, loaded_files)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}, 400


if __name__ == "__main__":
    try:
        print("[INFO] Starting Flask server. Press Ctrl+C to stop safely.")
        app.run(debug=True)
    finally:
        print("\n[INFO] Flask server stopped safely.")
        # Optional: any final cleanup here
