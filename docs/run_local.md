# MEDF Local Run Guide

Use these exact commands from the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Run tests (in a separate terminal with the same venv activated, or after stopping uvicorn):

```bash
source .venv/bin/activate
pytest
```

## Dev performance

Streamlit recommends `watchdog` for faster file watching during local development.

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run streamlit_app.py
```
