"""内容提取器

统一的文章内容提取，支持：
- trafilatura 通用提取
- BeautifulSoup 结构化提取
- 标题/日期/摘要的智能提取
"""

import hashlib
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from src.config.settings import MAX_SNIPPET_LENGTH, MAX_ARTICLES_PER_SOURCE

logger = logging.getLogger(__name__)


def extract_articles_from_html(
    html: str,
    base_url: str,
    source_name: str = "",
) -> list[dict]:
    """从HTML页面提取文章列表

    提取策略：
    1. 查找常见的文章列表容器
    2. 提取每篇文章的标题、链接、日期、摘要
    3. 使用trafilatura作为内容提取后备

    Returns:
        [{"title": ..., "url": ..., "date": ..., "snippet": ...}, ...]
    """
    if not html or not html.strip():
        return []

    soup = BeautifulSoup(html, "lxml")
    articles = []

    # 移除脚本和样式
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # 策略1: 查找article标签
    article_tags = soup.find_all("article")
    if article_tags:
        for tag in article_tags[:MAX_ARTICLES_PER_SOURCE]:
            art = _extract_from_tag(tag, base_url)
            if art and art.get("title"):
                articles.append(art)

    # 策略2: 查找常见列表项模式
    if not articles:
        # 查找包含链接的列表项 (li > a, div.card, div.post, etc.)
        selectors = [
            "li h2 a", "li h3 a", "li h4 a",
            ".card a", ".post a", ".item a",
            ".news-item a", ".article-item a", ".entry a",
            ".blog-post a", ".research-item a",
            "h2 a", "h3 a",
        ]
        seen_urls = set()
        for selector in selectors:
            links = soup.select(selector)
            for link in links[:MAX_ARTICLES_PER_SOURCE]:
                href = link.get("href", "")
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                full_url = urljoin(base_url, href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                title = link.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                # 尝试找到父容器获取更多信息
                parent = link.find_parent(["li", "div", "article", "section"])
                snippet = ""
                date = ""
                if parent:
                    # 提取摘要
                    p_tags = parent.find_all("p")
                    if p_tags:
                        snippet = " ".join(p.get_text(strip=True) for p in p_tags[:2])
                    # 提取日期
                    date = _extract_date_from_tag(parent)

                articles.append({
                    "title": title[:300],
                    "url": full_url,
                    "date": date,
                    "snippet": snippet[:MAX_SNIPPET_LENGTH] if snippet else "",
                })

            if len(articles) >= 5:
                break

    # 策略3: 使用trafilatura提取全文（如果页面只有一篇文章）
    if not articles:
        try:
            import trafilatura
            result = trafilatura.extract(
                html,
                include_links=True,
                include_comments=False,
                output_format="txt",
            )
            if result:
                title = _extract_page_title(soup)
                articles.append({
                    "title": title or source_name,
                    "url": base_url,
                    "date": _extract_date_from_tag(soup) or "",
                    "snippet": result[:MAX_SNIPPET_LENGTH],
                })
        except Exception as e:
            logger.debug("trafilatura提取失败: %s", e)

    # 如果还是空，用最基本的方式提取
    if not articles:
        title = _extract_page_title(soup)
        text = soup.get_text(separator=" ", strip=True)
        if title and len(text) > 100:
            articles.append({
                "title": title,
                "url": base_url,
                "date": "",
                "snippet": text[:MAX_SNIPPET_LENGTH],
            })

    return articles[:MAX_ARTICLES_PER_SOURCE]


def compute_content_hash(title: str, url: str) -> str:
    """计算内容哈希"""
    content = f"{title.strip().lower()}|{url.strip().lower()}"
    return hashlib.md5(content.encode()).hexdigest()


# ─── 内部辅助函数 ────────────────────────────────────────


def _extract_from_tag(tag, base_url: str) -> dict:
    """从HTML标签中提取文章信息"""
    result = {"title": "", "url": "", "date": "", "snippet": ""}

    # 提取标题和链接
    heading = tag.find(["h1", "h2", "h3", "h4"])
    if heading:
        link = heading.find("a")
        if link:
            result["title"] = link.get_text(strip=True)
            href = link.get("href", "")
            if href:
                result["url"] = urljoin(base_url, href)
        else:
            result["title"] = heading.get_text(strip=True)

    if not result["title"]:
        link = tag.find("a")
        if link:
            result["title"] = link.get_text(strip=True)
            href = link.get("href", "")
            if href:
                result["url"] = urljoin(base_url, href)

    if not result["url"]:
        result["url"] = base_url

    # 提取摘要
    p_tags = tag.find_all("p")
    if p_tags:
        result["snippet"] = " ".join(
            p.get_text(strip=True) for p in p_tags[:2]
        )[:MAX_SNIPPET_LENGTH]

    # 提取日期
    result["date"] = _extract_date_from_tag(tag)

    return result


def _extract_date_from_tag(tag) -> str:
    """从标签中提取日期"""
    # 方法1: time标签
    time_tag = tag.find("time")
    if time_tag:
        dt = time_tag.get("datetime", "") or time_tag.get_text(strip=True)
        if dt:
            return dt[:10]

    # 方法2: 日期class
    date_classes = ["date", "time", "published", "posted", "datetime", "timestamp"]
    for cls in date_classes:
        date_tag = tag.find(class_=re.compile(cls, re.I))
        if date_tag:
            text = date_tag.get_text(strip=True)
            if text and len(text) < 50:
                return text

    # 方法3: meta标签
    meta = tag.find("meta", attrs={"name": re.compile("date|time", re.I)})
    if meta:
        return meta.get("content", "")[:10]

    return ""


def _extract_page_title(soup: BeautifulSoup) -> str:
    """提取页面标题"""
    # 优先使用<title>
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
        # 清理常见的后缀
        for sep in [" | ", " - ", " — ", " :: ", " · "]:
            if sep in title:
                title = title.split(sep)[0].strip()
        if title:
            return title

    # 其次使用h1
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    # og:title
    og = soup.find("meta", property="og:title")
    if og:
        return og.get("content", "")

    return ""
