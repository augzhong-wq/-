"""HTTP采集器 - 基于httpx的异步采集

适用于大多数静态HTML网站。
特性：
- 异步HTTP请求
- User-Agent轮换
- 自动重试（3次，指数退避）
- 超时控制
"""

import asyncio
import logging
import random
from datetime import datetime

import httpx

from src.collectors.base import BaseCollector
from src.collectors.extractor import extract_articles_from_html, compute_content_hash
from src.config.settings import (
    USER_AGENTS, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF
)
from src.config.sources import Source
from src.database.models import RawArticle

logger = logging.getLogger(__name__)


class HttpCollector(BaseCollector):
    """基于httpx的HTTP采集器"""

    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建HTTP客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(REQUEST_TIMEOUT),
                follow_redirects=True,
                verify=False,  # 某些站点证书问题
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=20,
                ),
            )
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _get_headers(self) -> dict:
        """获取请求头（随机User-Agent）"""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

    async def _fetch_url(self, url: str) -> str | None:
        """获取URL内容，带重试"""
        client = await self._get_client()

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (403, 429):
                    wait = RETRY_BACKOFF ** (attempt + 1) + random.uniform(1, 3)
                    logger.warning(
                        "HTTP %d for %s, 等待 %.1fs 后重试 (%d/%d)",
                        e.response.status_code, url, wait,
                        attempt + 1, MAX_RETRIES
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.warning("HTTP %d for %s", e.response.status_code, url)
                    return None
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                wait = RETRY_BACKOFF ** (attempt + 1)
                logger.warning(
                    "连接错误 %s: %s, 等待 %ds 后重试 (%d/%d)",
                    url, type(e).__name__, wait,
                    attempt + 1, MAX_RETRIES
                )
                await asyncio.sleep(wait)
            except Exception as e:
                logger.warning("请求异常 %s: %s", url, e)
                return None

        logger.error("URL采集失败（已重试%d次）: %s", MAX_RETRIES, url)
        return None

    async def collect(self, source: Source) -> list[RawArticle]:
        """采集单个信息源的所有URL"""
        all_articles: list[RawArticle] = []
        collected_at = datetime.utcnow().isoformat()

        for url in source.urls:
            url = url.strip().rstrip(";")
            if not url:
                continue

            try:
                html = await self._fetch_url(url)
                if not html:
                    logger.warning("[HTTP] %s 无法获取: %s", source.name, url)
                    continue

                extracted = extract_articles_from_html(
                    html, url, source.name
                )

                for art in extracted:
                    if not art.get("title"):
                        continue

                    raw = RawArticle(
                        source_name=source.name,
                        source_category=source.category,
                        source_sub_category=source.sub_category,
                        url=art.get("url", url),
                        title=art["title"],
                        content_snippet=art.get("snippet", ""),
                        published_date=art.get("date", ""),
                        collected_at=collected_at,
                        content_hash=compute_content_hash(
                            art["title"], art.get("url", url)
                        ),
                    )
                    all_articles.append(raw)

                # 适当延迟，避免过快请求同域名
                await asyncio.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                logger.error(
                    "[HTTP] %s 采集异常 %s: %s",
                    source.name, url, e
                )

        logger.info(
            "[HTTP] %s: 完成采集 %d 个URL, 获取 %d 篇文章",
            source.name, len(source.urls), len(all_articles)
        )
        return all_articles
