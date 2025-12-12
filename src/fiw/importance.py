from __future__ import annotations

import math
import re

import pandas as pd

from fiw.sources import CATEGORY_RULES


def _contains_any(text: str, keywords: list[str]) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in keywords)


def infer_category(title: str, summary: str | None) -> str:
    text = f"{title} {summary or ''}"
    for cat, kws in CATEGORY_RULES.items():
        if _contains_any(text, kws):
            return cat
    return "其他"


def score_importance(title: str, summary: str | None, source_name: str, domain: str | None) -> tuple[float, str]:
    text = f"{title} {summary or ''}".lower()

    score = 0.0

    # 权威源加权
    authority = 0.0
    src = (source_name or "").lower()
    dom = (domain or "").lower()
    if any(x in src for x in ["white house", "eu", "oecd", "imf", "gov", "miit", "rand", "mit", "nature", "science"]):
        authority += 1.2
    if any(x in dom for x in [".gov", "whitehouse.gov", "europa.eu", "oecd.org", "imf.org"]):
        authority += 1.4
    score += authority

    # 事件类型
    policy_hits = [
        r"executive order",
        r"bill",
        r"act",
        r"regulation",
        r"sanction",
        r"export control",
        r"entity list",
        r"ofac",
        r"cfius",
        r"tariff",
        r"blacklist",
        r"national security",
        r"tariff",
        r"restriction",
        r"行政令",
        r"法案",
        r"制裁",
        r"反制",
        r"出口管制",
        r"禁令",
        r"实体清单",
        r"黑名单",
        r"关税",
        r"国家安全",
        r"审查",
        r"合规",
        r"监管",
    ]
    product_hits = [r"launch", r"release", r"unveil", r"announce", r"发布", r"推出", r"上线", r"量产"]
    money_hits = [r"funding", r"raised", r"series", r"acquisition", r"merger", r"ipo", r"融资", r"收购", r"并购", r"上市"]

    def _hit(patterns: list[str]) -> int:
        return sum(1 for p in patterns if re.search(p, text))

    score += 1.6 * min(3, _hit(policy_hits))
    score += 1.1 * min(3, _hit(product_hits))
    score += 1.0 * min(3, _hit(money_hits))

    # 影响范围提示词
    if re.search(r"global|world|nationwide|国家级|全国|全球", text):
        score += 0.8
    if re.search(r"multi-?billion|trillion|\b\d+\s*(billion|trillion)\b|千亿|万亿|百亿", text):
        score += 0.9
    if re.search(r"ban|prohibit|restrict|限制|禁止|暂停", text):
        score += 0.6
    if re.search(r"first|world first|首次|首个|全球首|里程碑|milestone", text):
        score += 0.5

    # 稳定化到 0-10
    score = 10.0 * (1.0 - math.exp(-score / 3.2))

    # 解释
    reasons = []
    if authority > 0:
        reasons.append("权威来源")
    if _hit(policy_hits) > 0:
        reasons.append("重大政策/管制")
    if _hit(product_hits) > 0:
        reasons.append("重大产品/技术发布")
    if _hit(money_hits) > 0:
        reasons.append("投融资/并购")
    if not reasons:
        reasons.append("行业动态")

    return score, "、".join(reasons)


def level_from_score(score: float) -> str:
    if score >= 8.2:
        return "S"
    if score >= 6.6:
        return "A"
    if score >= 4.6:
        return "B"
    return "C"


def enrich_importance(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()

    cats = []
    scores = []
    levels = []
    reasons = []

    for _, r in df.iterrows():
        title = str(r.get("title", ""))
        summary = r.get("summary")
        source_name = str(r.get("source_name", ""))
        domain = r.get("domain")

        cat = infer_category(title, summary if isinstance(summary, str) else None)
        score, reason = score_importance(title, summary if isinstance(summary, str) else None, source_name, str(domain) if domain else None)
        lvl = level_from_score(score)

        cats.append(cat)
        scores.append(f"{score:.2f}")
        levels.append(lvl)
        reasons.append(reason)

    df["category"] = cats
    df["importance_score"] = scores
    df["importance_level"] = levels
    df["importance_reason"] = reasons
    return df
