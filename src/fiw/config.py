from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    return v if v not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    raw_dir: Path
    daily_dir: Path
    weekly_dir: Path

    timezone: str

    # Optional push channels
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_pass: str | None
    smtp_from: str | None
    smtp_to: str | None

    wecom_webhook: str | None

    # Optional external APIs
    gdelt_user_agent: str
    newsapi_key: str | None


def load_settings() -> Settings:
    project_root = Path(_env("FIW_PROJECT_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()
    data_dir = Path(_env("FIW_DATA_DIR", str(project_root / "data"))).resolve()

    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        raw_dir=Path(_env("FIW_RAW_DIR", str(data_dir / "raw"))).resolve(),
        daily_dir=Path(_env("FIW_DAILY_DIR", str(data_dir / "daily"))).resolve(),
        weekly_dir=Path(_env("FIW_WEEKLY_DIR", str(data_dir / "weekly"))).resolve(),
        timezone=_env("FIW_TIMEZONE", "Asia/Shanghai") or "Asia/Shanghai",
        smtp_host=_env("FIW_SMTP_HOST"),
        smtp_port=int(_env("FIW_SMTP_PORT", "587") or 587),
        smtp_user=_env("FIW_SMTP_USER"),
        smtp_pass=_env("FIW_SMTP_PASS"),
        smtp_from=_env("FIW_SMTP_FROM"),
        smtp_to=_env("FIW_SMTP_TO"),
        wecom_webhook=_env("FIW_WECOM_WEBHOOK"),
        gdelt_user_agent=_env("FIW_GDELT_UA", "FutureIndustryWeeklyBot/0.1 (contact: you@example.com)")
        or "FutureIndustryWeeklyBot/0.1",
        newsapi_key=_env("FIW_NEWSAPI_KEY"),
    )
