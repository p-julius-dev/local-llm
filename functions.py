from ollama import chat
import uuid
from datetime import datetime

# ------------------------
# Helper Functions
# ------------------------

def generate_new_session_id():
    return str(uuid.uuid4())


def get_all_sessions(cursor):
    cursor.execute("""
        SELECT session_id, start_time, name
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
    default_name = "New Chat"
    start_time = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO sessions (start_time, name) VALUES (?, ?)",
        (start_time, default_name) 
    )

    session_id = cursor.lastrowid  # Get the auto-generated session_id
    return session_id, default_name

def save_message(cursor, session_id, role, content):
    """Save a message to the DB."""
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.now().isoformat())
    )

def recall_last_messages(messages, n=5):
    """recall and print last five messages"""
    last_n_messages = messages[-n:]
    
    print(f"\n--- Last {len(last_n_messages)} Messages (History) ---")
    for message in last_n_messages:
        print(f"[{message['role'].capitalize()}]: {message['content']}")
    print("-------------------------------------------\n")

# ------------------------
# Backend Function
# ------------------------
def process_user_message(cursor, session_id, messages, user_message):
    """
    Adds user message, saves to DB, calls LLM, returns assistant reply.
    """
    # Add user message
    messages.append({"role": "user", "content": user_message})
    save_message(cursor, session_id, "user", user_message)

    # Call LLM
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
            print(content, end="", flush=True)  # CLI streaming
            assistant_reply += content
    print("\n")

    # Save assistant reply
    messages.append({"role": "assistant", "content": assistant_reply})
    save_message(cursor, session_id, "assistant", assistant_reply)

    return assistant_reply

# Data filtering ORG
#def filter_dataset(df, column, value):
    #return df[df[column] == value]

# Data filtering new 4/18
def filter_dataset(df, column, value):
    try:
        # Attempt to coerce value to column dtype
        value = df[column].dtype.type(value)
    except:
        pass

    return df[df[column] == value]

# ------------------------
# Tool Registry 4/18
# ------------------------

TOOLS = {
    "filter_dataset": filter_dataset
}

# -----------------------
# Tool Execution Wrapper 4/18
# -----------------------
def execute_tool(action, parameters, loaded_files):
    if action not in TOOLS:
        raise ValueError(f"Unknown tool: {action}")

    if action == "filter_dataset":
        file = parameters.get("file")
        column = parameters.get("column")
        value = parameters.get("value")

        df = loaded_files.get(file)
        if df is None:
            raise ValueError("File not loaded")

        result_df = TOOLS[action](df, column, value)

        return {
            "columns": list(result_df.columns),
            "row_count": len(result_df),
            "preview": result_df.head(10).to_dict(orient="records")
        }

    # Future tools go here
    