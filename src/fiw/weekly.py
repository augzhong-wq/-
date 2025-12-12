from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from fiw.config import Settings
from fiw.dedupe import dedupe_by_title_url
from fiw.importance import enrich_importance
from fiw.io_csv import read_articles_csv
from fiw.pdf import render_weekly_pdf
from fiw.utils import week_id_from_monday


@dataclass
class WeeklyPackage:
    week_id: str
    week_start: date
    week_end: date
    weekly_dir: Path
    pdf_path: Path
    raw_merged_csv: Path
    top_csv: Path


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _parse_week_start(s: str | None) -> date:
    if s:
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    return _monday_of(date.today())


def build_daily_views(settings: Settings, day: date) -> tuple[Path, Path]:
    raw_path = settings.raw_dir / day.isoformat() / "articles_raw.csv"
    df = read_articles_csv(raw_path)
    df = dedupe_by_title_url(df)
    df = enrich_importance(df)
    # 补充 week_id 便于周聚合
    monday = _monday_of(day)
    wid = week_id_from_monday(monday)
    if not df.empty:
        df["week_id"] = wid

    # 完整版
    full_path = settings.daily_dir / day.isoformat() / "full.csv"
    full_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(full_path, index=False, encoding="utf-8-sig")

    # 精简版：只保留 B以上 + 每类最多 N 条
    keep = df[df["importance_level"].isin(["S", "A", "B"])].copy()
    keep["_score"] = keep["importance_score"].astype(float)
    keep = keep.sort_values(["_score"], ascending=False)
    brief = (
        keep.groupby("category", dropna=False)
        .head(30)
        .drop(columns=["_score"], errors="ignore")
        .reset_index(drop=True)
    )

    brief_path = settings.daily_dir / day.isoformat() / "brief.csv"
    brief.to_csv(brief_path, index=False, encoding="utf-8-sig")

    return full_path, brief_path


def build_weekly_package(settings: Settings, week_start: str | None = None) -> WeeklyPackage:
    monday = _parse_week_start(week_start)
    week_end = monday + timedelta(days=6)
    wid = week_id_from_monday(monday)

    # merge 7 days
    dfs = []
    for i in range(7):
        d = monday + timedelta(days=i)
        p = settings.daily_dir / d.isoformat() / "full.csv"
        if p.exists():
            dfs.append(pd.read_csv(p, dtype=str, keep_default_na=False))
    if dfs:
        df = pd.concat(dfs, ignore_index=True)
    else:
        df = pd.DataFrame()

    if not df.empty:
        df = dedupe_by_title_url(df)
        df = enrich_importance(df)

    out_dir = settings.weekly_dir / wid
    out_dir.mkdir(parents=True, exist_ok=True)

    merged_csv = out_dir / "week_all.csv"
    df.to_csv(merged_csv, index=False, encoding="utf-8-sig")

    # Top picks
    if not df.empty:
        df["_score"] = df["importance_score"].astype(float)
        top = df.sort_values(["_score"], ascending=False).head(60).drop(columns=["_score"], errors="ignore")
    else:
        top = df
    top_csv = out_dir / "week_top.csv"
    top.to_csv(top_csv, index=False, encoding="utf-8-sig")

    # PDF
    pdf_path = out_dir / f"未来产业周度要闻_{wid}.pdf"
    render_weekly_pdf(
        pdf_path=pdf_path,
        week_id=wid,
        monday=monday,
        keywords=["智能算力", "智能体", "具身智能"],
        df_top=top,
    )

    return WeeklyPackage(
        week_id=wid,
        week_start=monday,
        week_end=week_end,
        weekly_dir=out_dir,
        pdf_path=pdf_path,
        raw_merged_csv=merged_csv,
        top_csv=top_csv,
    )
