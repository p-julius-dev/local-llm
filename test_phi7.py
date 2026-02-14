from ollama import chat
import csv
#memory appending AND chat streaming AND saves entire messages dictionary to CSV on 'exit'
messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant. Answer clearly and concisely. Do not change the task."
    }
]

while True:
    question = input("Ask the model something (type 'exit' to quit): ")

    if question.lower() == "exit":

        with open("conversation_log.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["role","content"])

            for msg in messages:
                writer.writerow([msg["role"], msg["content"]])
        print("Goodbye")
        break


    messages.append({
        "role": "user",
        "content": question
    })

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

    messages.append({
        "role": "assistant",
        "content": assistant_reply
    })

