# Installation Guide — SQLite Edition

## Requirements

- Windows 10/11, Linux or macOS
- Python 3.10 or newer
- Internet access only for the first package installation

No external database software is required.

## Windows one-click setup

1. Extract the project ZIP.
2. Double-click `START_FINGUARD.bat`.
3. The launcher creates `.venv`, installs dependencies, creates encryption secrets, initializes `data/finguard_ai.db`, validates models, and starts Streamlit.

## Manual setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

python -m pip install -r requirements.txt
python scripts/preflight.py
python -m streamlit run app.py
```

## Reset Python environment

`RESET_AND_RUN.bat` removes only `.venv`. It preserves `data/finguard_ai.db`, encryption secrets, reports, backups and user data.
