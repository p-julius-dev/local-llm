from ollama import chat
from datetime import datetime
import os
import csv
import uuid
import sqlite3

# ensure db folder exists, if it does not exist, create
os.makedirs("db", exist_ok=True)

# database setup
db_path = "db/chat_sessions.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# create tables if they don't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions(
    session_id TEXT PRIMARY KEY,
    start_time TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages(
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT,
    content TEXT,
    timestamp TEXT,
    FOREIGN KEY(session_id) REFERENCES Sessions(session_id)
)
""")

# Generate session ID
session_id = str(uuid.uuid4())
start_time = datetime.now().isoformat()

cursor.execute(
    "INSERT INTO sessions (session_id, start_time) VALUES(?,?)",
    (session_id, start_time)
)
conn.commit()

print(f"\n=== SESSION START ===")
print(f"Session ID: {session_id}")
print("======================\n")


# Chat memory setup
messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant. Answer clearly and concisely. Do not change the task."
    }
]

# Conversation loop
while True:
    question = input("Ask the model something (type 'exit' to quit): ")

    if question.lower() == "exit":
        print("Goodbye")
        break

# add message to memory
    messages.append({"role": "user", "content": question})
# Insert user message inot db
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, "user", question, datetime.now().isoformat())
)
    conn.commit()

# Streaming chat
    print("\nPhi3 says:\n", end="", flush=True)

    stream = chat(
        model="phi3:mini",
        messages=messages,
        options={"temperature": 0.4},
        stream = True
    )

    assistant_reply = ""

    for chunk in stream:
        if "message" in chunk:
            content = chunk["message"]["content"]
            print(content, end="", flush = True)
            assistant_reply += content

    print("\n")
#Add assistant reply to memroy
    messages.append({"role": "assistant", "content": assistant_reply})

# Insert assistant message 
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, "assistant", assistant_reply, datetime.now().isoformat())
    )
    conn.commit()
# Cleanup
conn.close()

