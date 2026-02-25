# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

**Future Industry Weekly Post (未来产业周度要闻)** — automated news aggregation, importance scoring, and weekly PDF report generation. Single Python package (`fiw`) with a Flask dev dashboard.

### Prerequisites

- Python 3.10+ (system Python 3.12 works)
- Virtual environment at `.venv` (see README for setup)
- `.env` file copied from `.env.example`

### Key commands

All commands require the virtualenv activated: `source .venv/bin/activate`

| Task | Command |
|---|---|
| Install deps | `pip install -r requirements.txt && pip install -e .` |
| Build daily views | `python3 -m fiw build-daily --date 2025-12-12` |
| Build static site | `python3 -m fiw build-site --max-days 60` |
| Run dashboard | `python3 -m fiw serve --port 8080` |
| Collect articles | `python3 -m fiw collect --date YYYY-MM-DD` |
| Build weekly PDF | `python3 -m fiw build-weekly` |

### Notes

- The project has **no automated test suite** and **no linter configuration**. Validation is done by running the CLI commands and visually inspecting the dashboard / generated files.
- Sample data exists in `data/raw/2025-12-12/` for testing without network access.
- LLM features are optional; set `FIW_LLM_MODE=off` (default) to skip DeepSeek API calls.
- The `requests` library may emit a `RequestsDependencyWarning` about urllib3/chardet version mismatch — this is benign and does not affect functionality.
- The Flask dashboard binds to `0.0.0.0:8080` by default. Data is loaded from `data/daily/{date}/brief.csv` or `full.csv`.
- `python3.12-venv` system package must be installed (`sudo apt install python3.12-venv`) before creating the virtualenv.
