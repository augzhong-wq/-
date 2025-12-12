from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import feedparser
import requests

from fiw.config import Settings
from fiw.io_csv import write_articles_csv
from fiw.models import Article
from fiw.sources import load_sources
from fiw.utils import day_id, dump_json, iso_now, normalize_url, stable_id, url_domain


def _safe_get(d: dict, *keys: str):
    for k in keys:
        if k in d and d[k]:
            return d[k]
    return None


def _fetch_feed(url: str, ua: str) -> bytes | None:
    try:
        r = requests.get(url, headers={"User-Agent": ua}, timeout=15)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def _parse_rss(settings: Settings, rss_sources: list[dict], day: date, max_items: int = 800) -> list[Article]:
    out: list[Article] = []
    now = iso_now()
    for idx_src, src in enumerate(rss_sources, start=1):
        if idx_src % 10 == 0:
            print(f"[fiw] rss progress: {idx_src}/{len(rss_sources)}", flush=True)

        data = _fetch_feed(src["url"], ua=settings.gdelt_user_agent)
        if not data:
            continue
        try:
            feed = feedparser.parse(data)
        except Exception:
            continue
        entries = getattr(feed, "entries", []) or []
        for e in entries[: max_items // max(1, len(rss_sources)) + 50]:
            link = _safe_get(e, "link")
            title = _safe_get(e, "title")
            if not link or not title:
                continue
            link = normalize_url(link)
            published = _safe_get(e, "published", "updated")
            summary = _safe_get(e, "summary", "description")
            authors = _safe_get(e, "author")
            tags = None
            if "tags" in e and e["tags"]:
                tags = ",".join([t.get("term", "") for t in e["tags"] if t.get("term")]) or None

            aid = stable_id("rss", src["name"], link)
            out.append(
                Article(
                    id=aid,
                    collected_at=now,
                    published_at=published,
                    source_name=src["name"],
                    source_type="rss",
                    source_country=src.get("country"),
                    language=src.get("lang"),
                    title=title.strip(),
                    summary=(summary.strip() if isinstance(summary, str) and summary.strip() else None),
                    url=link,
                    authors=(authors.strip() if isinstance(authors, str) and authors.strip() else None),
                    tags=tags,
                    domain=url_domain(link),
                    category=None,
                    region=None,
                    importance_score=None,
                    importance_level=None,
                    importance_reason=None,
                    week_id=None,
                    day_id=day_id(day),
                    extra_json=dump_json({"rss": src, "raw": {"id": _safe_get(e, "id")}}),
                )
            )
    return out


def _gdelt_search(settings: Settings, query: str, max_records: int = 250) -> list[dict]:
    # GDELT DOC 2.1
    # https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(max_records),
        "formatdatetime": "true",
        "sort": "HybridRel",
    }
    headers = {"User-Agent": settings.gdelt_user_agent}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json().get("articles", []) or []


def _parse_gdelt(gdelt_queries: list[str], settings: Settings, day: date, max_items: int = 800) -> list[Article]:
    out: list[Article] = []
    now = iso_now()

    per_query = max(80, max_items // max(1, len(gdelt_queries)))
    for q in gdelt_queries:
        try:
            arts = _gdelt_search(settings, q, max_records=min(250, per_query))
        except Exception:
            continue
        for a in arts:
            link = a.get("url")
            title = a.get("title")
            if not link or not title:
                continue
            link = normalize_url(link)
            published = a.get("seendate") or a.get("date")
            summary = a.get("snippet")
            source = a.get("sourceCountry")
            lang = a.get("language")

            aid = stable_id("gdelt", a.get("domain", ""), link)
            out.append(
                Article(
                    id=aid,
                    collected_at=now,
                    published_at=published,
                    source_name=a.get("sourceCommonName") or a.get("domain") or "GDELT",
                    source_type="gdelt",
                    source_country=source,
                    language=lang,
                    title=str(title).strip(),
                    summary=(str(summary).strip() if summary else None),
                    url=link,
                    authors=None,
                    tags=None,
                    domain=a.get("domain") or url_domain(link),
                    category=None,
                    region=None,
                    importance_score=None,
                    importance_level=None,
                    importance_reason=None,
                    week_id=None,
                    day_id=day_id(day),
                    extra_json=dump_json({"gdelt": {k: a.get(k) for k in ("domain", "sourceCommonName", "socialimage", "tone", "sourceCountry")}}),
                )
            )
        time.sleep(0.3)
    return out


def collect_for_date(settings: Settings, day: date, max_items: int = 800) -> Path:
    rss_sources, gdelt_queries = load_sources(settings.project_root)
    print(f"[fiw] sources: rss={len(rss_sources)} gdelt_queries={len(gdelt_queries)}")
    rss = _parse_rss(settings=settings, rss_sources=rss_sources, day=day, max_items=max_items)
    print(f"[fiw] rss collected: {len(rss)}")
    gd = _parse_gdelt(gdelt_queries=gdelt_queries, settings=settings, day=day, max_items=max_items)
    print(f"[fiw] gdelt collected: {len(gd)}")

    # 简单合并（后续会有dedupe/importance再处理）
    seen: set[str] = set()
    merged: list[Article] = []
    for a in rss + gd:
        if a.id in seen:
            continue
        seen.add(a.id)
        merged.append(a)

    out_path = settings.raw_dir / day.isoformat() / "articles_raw.csv"
    write_articles_csv(out_path, merged)
    print(f"[fiw] wrote: {out_path} rows={len(merged)}")
    return out_path
