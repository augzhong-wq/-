"""浏览器采集器 - 基于Playwright的无头浏览器采集

适用于：
- JavaScript动态渲染页面
- 反爬严重的站点（AMD, Intel, Qualcomm等）
- 需要模拟真实浏览器行为的站点
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Optional

from src.collectors.base import BaseCollector
from src.collectors.extractor import extract_articles_from_html, compute_content_hash
from src.config.settings import (
    USER_AGENTS, BROWSER_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF
)
from src.config.sources import Source
from src.database.models import RawArticle

logger = logging.getLogger(__name__)


class BrowserCollector(BaseCollector):
    """基于Playwright的浏览器采集器"""

    def __init__(self):
        super().__init__()
        self._browser = None
        self._playwright = None

    async def _ensure_browser(self):
        """确保浏览器已启动"""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-blink-features=AutomationControlled",
                    ]
                )
                logger.info("Playwright浏览器启动成功")
            except Exception as e:
                logger.error("Playwright浏览器启动失败: %s", e)
                raise

    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def _fetch_page(self, url: str) -> str | None:
        """获取页面HTML，带重试"""
        await self._ensure_browser()

        for attempt in range(MAX_RETRIES):
            page = None
            try:
                context = await self._browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                page = await context.new_page()

                # 屏蔽不必要的资源
                await page.route(
                    "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,mp4,mp3}",
                    lambda route: route.abort()
                )

                await page.goto(url, wait_until="domcontentloaded",
                                timeout=BROWSER_TIMEOUT * 1000)

                # 等待内容加载
                await page.wait_for_timeout(3000)

                # 尝试关闭cookie弹窗
                await self._dismiss_cookie_banner(page)

                # 滚动以触发懒加载
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
                await page.wait_for_timeout(1000)

                html = await page.content()
                await page.close()
                await context.close()
                return html

            except Exception as e:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass
                wait = RETRY_BACKOFF ** (attempt + 1)
                logger.warning(
                    "浏览器获取失败 %s: %s, 等待 %ds (%d/%d)",
                    url, e, wait, attempt + 1, MAX_RETRIES
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(wait)

        logger.error("浏览器采集失败（已重试%d次）: %s", MAX_RETRIES, url)
        return None

    async def _dismiss_cookie_banner(self, page):
        """尝试关闭cookie/隐私弹窗"""
        button_selectors = [
            "button:has-text('Accept')",
            "button:has-text('Accept All')",
            "button:has-text('I Agree')",
            "button:has-text('OK')",
            "button:has-text('Got it')",
            "button:has-text('Close')",
            "[id*='cookie'] button",
            "[class*='cookie'] button",
            "[id*='consent'] button",
            "[class*='consent'] button",
        ]
        for selector in button_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    await btn.click(timeout=1000)
                    await page.wait_for_timeout(500)
                    return
            except Exception:
                continue

    async def collect(self, source: Source) -> list[RawArticle]:
        """采集单个信息源"""
        all_articles: list[RawArticle] = []
        collected_at = datetime.utcnow().isoformat()

        for url in source.urls:
            url = url.strip().rstrip(";")
            if not url:
                continue

            try:
                html = await self._fetch_page(url)
                if not html:
                    logger.warning("[Browser] %s 无法获取: %s", source.name, url)
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

                # 浏览器采集间隔稍长
                await asyncio.sleep(random.uniform(1.0, 3.0))

            except Exception as e:
                logger.error(
                    "[Browser] %s 采集异常 %s: %s",
                    source.name, url, e
                )

        logger.info(
            "[Browser] %s: 完成采集 %d 个URL, 获取 %d 篇文章",
            source.name, len(source.urls), len(all_articles)
        )
        return all_articles
