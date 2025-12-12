from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


@dataclass
class DedupeResult:
    df: pd.DataFrame
    clusters: dict[int, list[int]]  # cluster_id -> row indices


def dedupe_by_title_url(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["_url"] = df["url"].astype(str).str.strip()
    df["_title"] = df["title"].astype(str).map(_norm_text)
    df = df.drop_duplicates(subset=["_url"], keep="first")
    df = df.drop_duplicates(subset=["_title"], keep="first")
    return df.drop(columns=["_url", "_title"], errors="ignore")


def cluster_by_title(df: pd.DataFrame, threshold: float = 0.86) -> DedupeResult:
    if df.empty:
        return DedupeResult(df=df, clusters={})

    titles = df["title"].astype(str).fillna("").tolist()
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=40000)
    X = vec.fit_transform([_norm_text(t) for t in titles])
    sim = cosine_similarity(X)

    n = sim.shape[0]
    visited = np.zeros(n, dtype=bool)
    clusters: dict[int, list[int]] = {}
    cid = 0

    for i in range(n):
        if visited[i]:
            continue
        members = [i]
        visited[i] = True
        # BFS
        queue = [i]
        while queue:
            j = queue.pop()
            near = np.where((sim[j] >= threshold) & (~visited))[0]
            for k in near.tolist():
                visited[k] = True
                members.append(k)
                queue.append(k)
        clusters[cid] = members
        cid += 1

    return DedupeResult(df=df, clusters=clusters)
