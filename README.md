# Local LLM

**Local LLM** is a Python-based chatbot project using Ollama models to simulate conversations.  
It is designed as a local, extensible AI assistant with future plans to integrate SQLite for conversation persistence.

---

## Prerequisites

- Python 3.11+  
- [Ollama](https://ollama.com/) installed and configured  
- SQLite3 (standard with Python)  
- pip package manager  

---
### Pull / Set Up the Ollama Model

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

1. Clone the repository:

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
Usage

Run the main script:
```bash
python test_phi7.py
```
The script will generate conversation logs in conversation_log.csv (ignored in Git).

Future database integration will store conversations in SQLite.

Project Structure
```
local_llm/
├── test_phi7.py          # Main chatbot logic
├── phi_env/              # Virtual environment (ignored)
├── conversation_log.csv  # Runtime conversation logs (ignored)
├── .gitignore            # Ignored files/folders
├── requirements.txt      # Project dependencies
├── README.md             # Project overview and instructions
```
Notes

    Do not commit phi_env/ or runtime logs; they are machine-specific.

    For future development: integrate SQLite for persistent storage and modularize model wrappers.



