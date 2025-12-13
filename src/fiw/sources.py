from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# 采集源：优先用 RSS + 官方发布 + 智库/学术机构 + 政府/国际组织。
# 说明：部分媒体（如 WSJ/FT/Bloomberg）可能有付费墙；本项目只使用其公开 RSS/公开新闻室入口。

# 默认源（当 config/sources.yaml 不存在时使用）
DEFAULT_RSS_SOURCES = [
    # --- 国际综合/科技媒体 ---
    {
        "name": "MIT News",
        "url": "https://news.mit.edu/rss/feed",
        "country": "US",
        "lang": "en",
        "type": "academic",
    },
    {
        "name": "RAND",
        "url": "https://www.rand.org/rss.xml",
        "country": "US",
        "lang": "en",
        "type": "thinktank",
    },
    {
        "name": "Nature",
        "url": "https://www.nature.com/subjects/artificial-intelligence.rss",
        "country": "UK",
        "lang": "en",
        "type": "academic",
    },
    {
        "name": "Science",
        "url": "https://www.science.org/rss/news_current.xml",
        "country": "US",
        "lang": "en",
        "type": "academic",
    },
    {
        "name": "arXiv CS",
        "url": "http://export.arxiv.org/rss/cs",
        "country": "US",
        "lang": "en",
        "type": "academic",
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "country": "US",
        "lang": "en",
        "type": "media",
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "country": "US",
        "lang": "en",
        "type": "media",
    },
    {
        "name": "Ars Technica",
        "url": "http://feeds.arstechnica.com/arstechnica/index",
        "country": "US",
        "lang": "en",
        "type": "media",
    },
    {
        "name": "Wired",
        "url": "https://www.wired.com/feed/rss",
        "country": "US",
        "lang": "en",
        "type": "media",
    },
    {
        "name": "IEEE Spectrum",
        "url": "https://spectrum.ieee.org/rss/fulltext",
        "country": "US",
        "lang": "en",
        "type": "media",
    },
    {
        "name": "NVIDIA Blog",
        "url": "https://blogs.nvidia.com/feed/",
        "country": "US",
        "lang": "en",
        "type": "company",
    },
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "country": "US",
        "lang": "en",
        "type": "company",
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
        "country": "US",
        "lang": "en",
        "type": "company",
    },
    {
        "name": "AWS News Blog",
        "url": "https://aws.amazon.com/blogs/aws/feed/",
        "country": "US",
        "lang": "en",
        "type": "company",
    },
    {
        "name": "Microsoft AI Blog",
        "url": "https://blogs.microsoft.com/ai/feed/",
        "country": "US",
        "lang": "en",
        "type": "company",
    },
    {
        "name": "DeepMind",
        "url": "https://deepmind.google/discover/blog/rss.xml",
        "country": "UK",
        "lang": "en",
        "type": "company",
    },
    {
        "name": "EU Commission - Press",
        "url": "https://ec.europa.eu/commission/presscorner/api/rss?language=en",
        "country": "EU",
        "lang": "en",
        "type": "policy",
    },
    {
        "name": "White House - Briefing Room",
        "url": "https://www.whitehouse.gov/briefing-room/feed/",
        "country": "US",
        "lang": "en",
        "type": "policy",
    },
    {
        "name": "UK Government - News",
        "url": "https://www.gov.uk/search/news-and-communications.atom?content_store_document_type=press_release",
        "country": "UK",
        "lang": "en",
        "type": "policy",
    },
    {
        "name": "OECD - News",
        "url": "https://www.oecd.org/newsroom/rss.xml",
        "country": "OECD",
        "lang": "en",
        "type": "policy",
    },
    {
        "name": "World Economic Forum",
        "url": "https://www.weforum.org/agenda/rss.xml",
        "country": "CH",
        "lang": "en",
        "type": "thinktank",
    },
    {
        "name": "IMF - News",
        "url": "https://www.imf.org/external/rss/feeds.aspx?category=News",
        "country": "US",
        "lang": "en",
        "type": "policy",
    },
    # --- 付费媒体：仅公开RSS（可用性取决于对方策略） ---
    {
        "name": "Wall Street Journal - World News (RSS)",
        "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "country": "US",
        "lang": "en",
        "type": "media",
    },
    # --- 国内（尽量使用公开RSS/公告） ---
    {
        "name": "工信部",
        "url": "https://www.miit.gov.cn/rss/jgsj/index.xml",
        "country": "CN",
        "lang": "zh",
        "type": "policy",
    },
]

# GDELT 查询主题（每天会用这些关键词“海量”检索，并与RSS去重合并）
DEFAULT_GDELT_QUERIES = [
    # 算力/芯片
    "(AI OR artificial intelligence) (GPU OR TPU OR accelerator OR HBM OR compute) (export control OR sanction OR ban OR restriction OR policy)",
    # 机器人/具身
    "(humanoid OR robot OR embodied AI) (launch OR release OR breakthrough OR deployment)",
    # 大模型/Agent
    "(foundation model OR LLM OR agentic AI) (release OR open-source OR benchmark OR regulation)",
    # 国家政策
    "(executive order OR bill OR act OR regulation OR ministry) (AI OR semiconductors OR robotics)",
    # 投融资/并购
    "(AI OR semiconductor OR robotics) (funding OR investment OR acquisition OR merger)",
]


def load_sources(project_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """
    从 `config/sources.yaml` 加载 RSS 源与 GDELT 查询；若不存在则回退到默认配置。
    """
    cfg = (project_root / "config" / "sources.yaml").resolve()
    if not cfg.exists():
        return DEFAULT_RSS_SOURCES, DEFAULT_GDELT_QUERIES

    data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    rss_sources = data.get("rss_sources") or DEFAULT_RSS_SOURCES
    gdelt_queries = data.get("gdelt_queries") or DEFAULT_GDELT_QUERIES
    return rss_sources, gdelt_queries

# 关键词分类（用于重要性打分与栏目归类）
CATEGORY_RULES = {
    "政策": [
        "executive order",
        "bill",
        "act",
        "sanction",
        "export control",
        "regulation",
        "ministry",
        "白宫",
        "国务院",
        "工信部",
        "发改委",
        "立法",
        "制裁",
        "反制",
        "行政令",
        "法案",
        "条例",
        "监管",
    ],
    "企业": [
        "launch",
        "release",
        "product",
        "chip",
        "model",
        "platform",
        "发布",
        "上线",
        "新品",
        "量产",
        "合作",
        "战略",
    ],
    "学术": [
        "paper",
        "arxiv",
        "nature",
        "science",
        "研究",
        "论文",
        "实验",
        "突破",
    ],
    "投融资": [
        "funding",
        "raised",
        "series",
        "IPO",
        "acquisition",
        "merger",
        "融资",
        "并购",
        "收购",
        "上市",
    ],
    "安全": [
        "cyber",
        "security",
        "vulnerability",
        "attack",
        "安全",
        "漏洞",
        "攻击",
        "风险",
    ],
}
