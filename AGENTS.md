# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

This is **Future Industry Weekly Post (未来产业周度要闻)** — an automated news aggregation and analysis system for AI, semiconductors, robotics, and tech policy news. It is a single Python application (package name `fiw`).

### Development environment

- **Python 3.10+** required (3.12 tested). The venv lives at `.venv/`.
- Activate with: `source .venv/bin/activate`
- Dependencies: `pip install -r requirements.txt && pip install -e .`
- Copy `.env.example` to `.env` before first run. Set `FIW_LLM_MODE=off` to skip DeepSeek API calls when no API key is available.

### Key CLI commands (see README for full details)

All commands use `python3 -m fiw <subcommand>`:

| Command | Description |
|---|---|
| `python3 -m fiw collect --date YYYY-MM-DD` | Collect news for a given date (requires internet) |
| `python3 -m fiw build-daily --date YYYY-MM-DD` | Build daily views from raw data |
| `python3 -m fiw build-site --max-days 60` | Generate static site |
| `python3 -m fiw serve --port 8080` | Start Flask dashboard |
| `python3 -m fiw build-weekly` | Generate weekly PDF report |

### Non-obvious gotchas

- The `collect` command requires outbound HTTP access to RSS feeds and GDELT API. It may take several minutes depending on feed availability.
- Pre-existing sample data is in `data/raw/2025-12-12/` and `data/daily/2025-12-12/`. Use `--date 2025-12-12` for testing without network access.
- The dashboard serves data from `data/daily/` CSV files. The `?day=YYYY-MM-DD` query parameter selects the date to view.
- There is no automated test suite in this repository. Verification is done by running CLI commands and checking output files / the dashboard.
- A `RequestsDependencyWarning` about urllib3/chardet version mismatch is harmless and can be ignored.
- `python3.12-venv` system package must be installed (`sudo apt-get install -y python3.12-venv`) before creating the virtualenv.
