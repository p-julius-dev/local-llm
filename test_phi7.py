import os
import sqlite3
from datetime import datetime
from ollama import chat 
from functions import (
    generate_new_session_id,
    get_all_sessions,
    load_session_messages,
    create_new_session,
    save_message
)

DB_PATH = "db/chat_sessions.db"

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

# ------------------------
# Session Loader
# ------------------------
def load_or_create_session(cursor):
    """
    Handles CLI session selection or creates new session.
    Returns (session_id, messages)
    """
    sessions = get_all_sessions(cursor)

    if sessions:
        print("\nAvailable Sessions:")
        for i, (s_id, start_time) in enumerate(sessions, start=1):
            print(f"{i}) {start_time}  |  {s_id}")

        user_choice = input(
            "\nSelect a session number to resume or type 'new' to start a new one: "
        ).strip()

        if user_choice.lower() == "new":
            session_id, start_time = create_new_session(cursor)
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Answer clearly and concisely. Do not change the task."}
            ]
            print(f"\n=== NEW SESSION STARTED | {session_id} ===\n")
        else:
            try:
                selection = int(user_choice)
                session_id, start_time = sessions[selection - 1]
                messages = load_session_messages(cursor, session_id)
                print(f"\n=== RESUMING SESSION | {session_id} | {len(messages)} messages ===\n")
            except (ValueError, IndexError):
                session_id, start_time = create_new_session(cursor)
                messages = [
                    {"role": "system", "content": "You are a helpful assistant. Answer clearly and concisely. Do not change the task."}
                ]
                print(f"\n=== INVALID SELECTION, NEW SESSION STARTED | {session_id} ===\n")
    else:
        # No sessions exist yet
        session_id, start_time = create_new_session(cursor)
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Answer clearly and concisely. Do not change the task."}
        ]
        print(f"\n=== FIRST SESSION CREATED | {session_id} ===\n")

    return session_id, messages

# ------------------------
# Main CLI Adapter
# ------------------------
def main():
    os.makedirs("db", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables if not exist
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
        FOREIGN KEY(session_id) REFERENCES sessions(session_id)
    )
    """)
    conn.commit()

    # Load or create session
    session_id, messages = load_or_create_session(cursor)

    # CLI Chat Loop
    while True:
        question = input("Ask the model something (type 'exit' to quit): ")
        if question.lower() == "exit":
            print("Goodbye")
            break

        process_user_message(cursor, session_id, messages, question)

    conn.close()



if __name__ == "__main__":
    main()