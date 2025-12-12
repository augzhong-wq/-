from __future__ import annotations

from pathlib import Path

import pandas as pd

from fiw.models import Article


CSV_COLUMNS = [
    "id",
    "collected_at",
    "published_at",
    "source_name",
    "source_type",
    "source_country",
    "language",
    "title",
    "summary",
    "url",
    "authors",
    "tags",
    "domain",
    "category",
    "region",
    "importance_score",
    "importance_level",
    "importance_reason",
    "week_id",
    "day_id",
    "extra_json",
]


def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def write_articles_csv(path: Path, articles: list[Article]) -> None:
    ensure_parent(path)
    df = pd.DataFrame([a.to_row() for a in articles])
    for c in CSV_COLUMNS:
        if c not in df.columns:
            df[c] = None
    df = df[CSV_COLUMNS]
    df.to_csv(path, index=False, encoding="utf-8-sig")


def read_articles_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=CSV_COLUMNS)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def append_articles_csv(path: Path, articles: list[Article]) -> None:
    ensure_parent(path)
    df_new = pd.DataFrame([a.to_row() for a in articles])
    if path.exists():
        df_old = pd.read_csv(path, dtype=str, keep_default_na=False)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_csv(path, index=False, encoding="utf-8-sig")
