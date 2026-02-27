# Local LLM

**Local LLM** is a Python-based chatbot project that runs Ollama models locally and stores conversations in SQLite with session-based persistence.

The project is structured for incremental feature development using Git branches and tagged milestones.

## Current Features

Local model execution via Ollama

SQLite-backed conversation storage

Session-based conversation tracking

Resume previous sessions

Clean version control workflow with tagged milestones

## Milestones

 - v0.1-basic-llm — Initial local chatbot

 - v0.2-resume-sessions — SQLite integration with session resume support

---

## Prerequisites

- Python 3.11+  
- [Ollama](https://ollama.com/) installed and configured  
- SQLite3 (standard with Python)  
- pip package manager  

---
### Set Up the Ollama Model

Check your Ollama installation:
```bash
ollama --version
```
as long as it returns a version, you are OK to proceed

Pull the model you want (example: phi3:mini):
```bash
ollama pull phi3:mini
```

Verify the model is installed:
```bash
ollama list
```
## Installation

Clone the repository:

```bash
git clone https://github.com/p-julius-dev/local-llm.git
cd local-llm
```
Create a virtual environment:
```bash
python -m venv phi_env
```

Activate the virtual environment:

    Windows (Git Bash / cmd):
```bash
source phi_env/Scripts/activate
```
    Mac/Linux:
```bash
source phi_env/bin/activate
```
Install required Python packages:
```bash
pip install -r requirements.txt
```
## Usage

Run the main script:
```bash
python test_phi7.py
```
The application:
- Creates/uses a local SQLite database (ignored in Git)
- Stores conversations by session_id
- Allows resuming previous sessions

## Architecture Notes

The application follows a simple but extensible structure:
- Each conversation is assigned a unique session_id (UUID).
- Messages are stored in SQLite with fields such as:
    - session_id
    - role (user / assistant)
    - content
    - timestamp

- On startup, the user can:
    - Start a new session
    - Resume an existing session

- When resuming, previous messages are loaded from the database and passed back to the model to preserve conversational context.

This structure separates:
- Model interaction logic
- Persistence (SQLite storage)
- Session lifecycle management

It provides a clean foundation for future features such as export tools, visualization, or reinforcement learning experimentation.

## Project Structure
```
local_llm/
├── test_phi7.py          # Main chatbot logic
├── db/                   # SQLite database (ignored)
├── phi_env/              # Virtual environment (ignored)
├── .gitignore
├── requirements.txt
├── README.md
```

## Roadmap

- CSV → XLSX export

- Conversation visualization

- Editor assistant mode

- Modular architecture refactor

- Optional cloud-deploy fork for portfolio demo

- Experimental reinforcement learning extensions

## Notes
Do not commit phi_env/ or runtime logs; they are machine-specific.

> “Be excellent to each other.”  
> — Bill & Ted