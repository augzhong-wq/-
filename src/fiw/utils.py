from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from urllib.parse import urlparse


def iso_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def normalize_url(u: str) -> str:
    u = u.strip()
    return u


def url_domain(u: str) -> str | None:
    try:
        return urlparse(u).netloc.lower() or None
    except Exception:
        return None


def stable_id(*parts: str) -> str:
    raw = "|".join([p.strip() for p in parts if p is not None])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def day_id(d: date) -> str:
    return d.isoformat()


def week_id_from_monday(monday: date) -> str:
    year, week, _ = monday.isocalendar()
    return f"{year}-{week:02d}"


def dump_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
