import os
import sqlite3
import uuid
from datetime import datetime
from ollama import chat 

DB_PATH = "db/chat_sessions.db"


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


# ------------------------
# Main Program
# ------------------------

def main():
    # Ensure db folder exists
    os.makedirs("db", exist_ok=True)

    # Database setup
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables if they don't exist
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

    # ------------------------
    # Startup: New or Resume
    # ------------------------

    sessions = get_all_sessions(cursor)

    if sessions:
        print("\nAvailable Sessions:")
        for i, (s_id, start_time) in enumerate(sessions, start=1):
            print(f"{i}) {start_time}  |  {s_id}")

        user_choice = input(
            "\nSelect a session number to resume or type 'new' to start a new one: "
        ).strip()

        if user_choice.lower() == "new":
            session_id = generate_new_session_id()
            start_time = datetime.now().isoformat()

            cursor.execute(
                "INSERT INTO sessions (session_id, start_time) VALUES (?, ?)",
                (session_id, start_time)
            )
            conn.commit()

            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Answer clearly and concisely. Do not change the task."
                }
            ]

            print("\n=== NEW SESSION STARTED ===")
            print(f"Session ID: {session_id}")
            print("============================\n")

        else:
            try:
                selection = int(user_choice)
                session_id, start_time = sessions[selection - 1]

                messages = load_session_messages(cursor, session_id)

                print("\n=== RESUMING SESSION ===")
                print(f"Session ID: {session_id}")
                print(f"Messages Loaded: {len(messages)}")
                print("========================\n")

            except (ValueError, IndexError):
                print("Invalid selection. Starting a new session.")
                session_id = generate_new_session_id()
                start_time = datetime.now().isoformat()

                cursor.execute(
                    "INSERT INTO sessions (session_id, start_time) VALUES (?, ?)",
                    (session_id, start_time)
                )
                conn.commit()

                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Answer clearly and concisely. Do not change the task."
                    }
                ]

    else:
        # No sessions exist yet
        session_id = generate_new_session_id()
        start_time = datetime.now().isoformat()

        cursor.execute(
            "INSERT INTO sessions (session_id, start_time) VALUES (?, ?)",
            (session_id, start_time)
        )
        conn.commit()

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer clearly and concisely. Do not change the task."
            }
        ]

        print("\n=== FIRST SESSION CREATED ===")
        print(f"Session ID: {session_id}")
        print("=============================\n")

    # ------------------------
    # Chat Loop
    # ------------------------

    while True:
        question = input("Ask the model something (type 'exit' to quit): ")

        if question.lower() == "exit":
            print("Goodbye")
            break

        # Add user message to memory
        messages.append({"role": "user", "content": question})

        # Save user message to DB
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
            stream=True
        )

        assistant_reply = ""

        for chunk in stream:
            if "message" in chunk:
                content = chunk["message"]["content"]
                print(content, end="", flush=True)
                assistant_reply += content

        print("\n")

        # Add assistant reply to memory
        messages.append({"role": "assistant", "content": assistant_reply})

        # Save assistant message
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, "assistant", assistant_reply, datetime.now().isoformat())
        )
        conn.commit()

    conn.close()


if __name__ == "__main__":
    main()