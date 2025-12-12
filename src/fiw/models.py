from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class Article:
    id: str
    collected_at: str
    published_at: str | None

    source_name: str
    source_type: str  # rss|gdelt|api|manual
    source_country: str | None
    language: str | None

    title: str
    summary: str | None
    url: str

    authors: str | None
    tags: str | None

    # Normalized fields
    domain: str | None
    category: str | None  # 企业|学术|政策|投融资|产业|安全|其他
    region: str | None

    importance_score: float | None
    importance_level: str | None  # S|A|B|C
    importance_reason: str | None

    week_id: str | None
    day_id: str

    extra_json: str | None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)
