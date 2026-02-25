"""浏览器采集器 - 基于Playwright的无头浏览器采集

三级采集策略：
1. Stealth浏览器模式 — 模拟真人浏览器指纹，绕过大部分反爬
2. HTML解析提取 — 从渲染后的DOM中提取文章
3. 截图+OCR降级 — 对于连浏览器都拦截的站点，截屏后用OCR提取文字

适用于：
- JavaScript动态渲染页面
- 反爬严重的站点（麦肯锡、xAI、Alan Turing等）
- 需要模拟真实浏览器行为的站点
"""

import asyncio
import logging
import os
import random
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.collectors.base import BaseCollector
from src.collectors.extractor import extract_articles_from_html, compute_content_hash
from src.config.settings import (
    USER_AGENTS, BROWSER_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF,
    MAX_SNIPPET_LENGTH, MAX_ARTICLES_PER_SOURCE,
)
from src.config.sources import Source
from src.database.models import RawArticle

logger = logging.getLogger(__name__)


class BrowserCollector(BaseCollector):
    """基于Playwright的浏览器采集器（含截图OCR降级）"""

    def __init__(self):
        super().__init__()
        self._browser = None
        self._playwright = None

    async def _ensure_browser(self):
        """确保浏览器已启动（增强反检测）"""
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
                        # 反检测参数
                        "--disable-blink-features=AutomationControlled",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--disable-web-security",
                        "--window-size=1920,1080",
                    ]
                )
                logger.info("Playwright浏览器启动成功（增强反检测模式）")
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

    async def _create_stealth_context(self):
        """创建带反检测的浏览器上下文"""
        ua = random.choice(USER_AGENTS)
        context = await self._browser.new_context(
            user_agent=ua,
            viewport={"width": 1920, "height": 1080},
            locale="en-US,en;q=0.9",
            timezone_id="America/New_York",
            # 模拟真实设备
            screen={"width": 1920, "height": 1080},
            color_scheme="light",
            java_script_enabled=True,
            # 禁用 webdriver 标记
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            },
        )
        return context

    async def _apply_stealth_scripts(self, page):
        """注入反检测脚本（隐藏自动化痕迹）"""
        await page.add_init_script("""
            // 隐藏 webdriver 标记
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // 模拟真实的 chrome 对象
            window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };

            // 伪造 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // 伪造 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // 隐藏 headless 标记
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });

            // 伪造 permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

    async def _fetch_page(self, url: str) -> tuple[str | None, bytes | None]:
        """获取页面HTML和截图

        Returns:
            (html_content, screenshot_bytes) — 截图作为OCR降级用
        """
        await self._ensure_browser()

        for attempt in range(MAX_RETRIES):
            context = None
            page = None
            try:
                context = await self._create_stealth_context()
                page = await context.new_page()

                # 注入反检测脚本
                await self._apply_stealth_scripts(page)

                # 第一次访问不屏蔽图片（某些反爬检测会检查）
                await page.goto(url, wait_until="domcontentloaded",
                                timeout=BROWSER_TIMEOUT * 1000)

                # 模拟真人行为：随机等待
                await page.wait_for_timeout(random.randint(2000, 4000))

                # 尝试关闭cookie弹窗
                await self._dismiss_cookie_banner(page)

                # 模拟滚动（真人行为）
                await self._human_scroll(page)

                # 获取HTML
                html = await page.content()

                # 检查是否被反爬拦截（页面内容太短或包含拦截关键词）
                is_blocked = self._check_if_blocked(html)

                screenshot = None
                if is_blocked:
                    logger.warning("[Browser] %s 疑似被反爬拦截，尝试截图OCR", url)
                    # 即使被拦截，也可能有部分内容可见，截图备用
                    screenshot = await page.screenshot(full_page=True, type="png")
                    html = None  # 标记HTML无效
                else:
                    # HTML有效，也截个图备用（用于提取HTML解析失败的情况）
                    screenshot = await page.screenshot(full_page=True, type="png")

                await page.close()
                await context.close()
                return html, screenshot

            except Exception as e:
                if page:
                    try:
                        # 失败时也尝试截图
                        screenshot = await page.screenshot(
                            full_page=True, type="png"
                        )
                    except Exception:
                        screenshot = None
                    try:
                        await page.close()
                    except Exception:
                        pass
                if context:
                    try:
                        await context.close()
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
        return None, None

    async def _human_scroll(self, page):
        """模拟真人滚动行为"""
        try:
            # 缓慢滚动到页面1/3处
            await page.evaluate("""
                async () => {
                    const totalHeight = document.body.scrollHeight;
                    const step = totalHeight / 10;
                    for (let i = 0; i < 3; i++) {
                        window.scrollBy(0, step);
                        await new Promise(r => setTimeout(r, 300 + Math.random() * 500));
                    }
                }
            """)
            await page.wait_for_timeout(random.randint(500, 1500))
        except Exception:
            pass

    def _check_if_blocked(self, html: str) -> bool:
        """检查页面是否被反爬拦截"""
        if not html:
            return True

        # 页面太短（可能是空白或错误页）
        text_content = re.sub(r'<[^>]+>', '', html).strip()
        if len(text_content) < 200:
            return True

        # 常见拦截标志
        block_indicators = [
            "access denied",
            "403 forbidden",
            "captcha",
            "cloudflare",
            "please verify you are human",
            "bot detection",
            "automated access",
            "rate limited",
            "too many requests",
            "please enable javascript",
            "challenge-platform",
        ]
        html_lower = html.lower()
        matches = sum(1 for ind in block_indicators if ind in html_lower)
        return matches >= 2

    async def _dismiss_cookie_banner(self, page):
        """尝试关闭cookie/隐私弹窗"""
        button_selectors = [
            "button:has-text('Accept')",
            "button:has-text('Accept All')",
            "button:has-text('Accept Cookies')",
            "button:has-text('I Agree')",
            "button:has-text('OK')",
            "button:has-text('Got it')",
            "button:has-text('Close')",
            "button:has-text('Dismiss')",
            "[id*='cookie'] button",
            "[class*='cookie'] button",
            "[id*='consent'] button",
            "[class*='consent'] button",
            "[id*='onetrust'] button",
            "[class*='onetrust'] button",
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

    def _ocr_extract_articles(
        self, screenshot: bytes, url: str, source_name: str
    ) -> list[dict]:
        """从截图中OCR提取文章信息

        使用 pytesseract 进行OCR，从截图中提取可见文字，
        然后按行分析提取可能的文章标题。
        """
        try:
            import pytesseract
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(screenshot))

            # OCR 提取文字（支持中英文）
            try:
                text = pytesseract.image_to_string(img, lang='eng+chi_sim')
            except Exception:
                # 如果没有中文语言包，只用英文
                text = pytesseract.image_to_string(img, lang='eng')

            if not text or len(text.strip()) < 50:
                logger.warning("[OCR] %s 提取文字过少", url)
                return []

            logger.info("[OCR] %s 提取到 %d 字符", url, len(text))

            # 从OCR文字中提取文章
            return self._parse_ocr_text(text, url, source_name)

        except ImportError:
            logger.warning("[OCR] pytesseract未安装，尝试基础文字提取")
            return self._basic_screenshot_extract(screenshot, url, source_name)
        except Exception as e:
            logger.error("[OCR] 提取失败 %s: %s", url, e)
            return []

    def _basic_screenshot_extract(
        self, screenshot: bytes, url: str, source_name: str
    ) -> list[dict]:
        """基础截图提取（不依赖pytesseract）

        当OCR不可用时，至少记录一条"此源需要截图OCR"的文章，
        并保存截图供人工处理。
        """
        # 保存截图到临时目录
        screenshot_dir = Path("data/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_{timestamp}.png"
        filepath = screenshot_dir / filename
        filepath.write_bytes(screenshot)
        logger.info("[Screenshot] 已保存截图: %s", filepath)

        return [{
            "title": f"[截图采集] {source_name} - 需要人工处理",
            "url": url,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "snippet": f"此信息源使用截图采集，截图已保存至 {filepath}。"
                       f"原始页面可能有反爬保护。",
        }]

    def _parse_ocr_text(
        self, text: str, url: str, source_name: str
    ) -> list[dict]:
        """从OCR文字中解析文章标题和摘要

        策略：
        1. 按行分割
        2. 筛选出可能是标题的行（长度适中、不是菜单/导航）
        3. 组合标题+后续行作为摘要
        """
        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip() and len(line.strip()) > 5
        ]

        if not lines:
            return []

        articles = []
        skip_patterns = [
            r"^(home|about|contact|menu|search|login|sign|cookie|privacy)",
            r"^(©|copyright|all rights)",
            r"^\d+$",  # 纯数字
            r"^[.\-_=]+$",  # 分隔线
        ]

        i = 0
        while i < len(lines) and len(articles) < MAX_ARTICLES_PER_SOURCE:
            line = lines[i]

            # 跳过导航/菜单行
            skip = False
            for pat in skip_patterns:
                if re.match(pat, line.lower()):
                    skip = True
                    break
            if skip:
                i += 1
                continue

            # 可能的标题行特征：10-200字符，首字母大写或包含中文
            if 10 <= len(line) <= 200:
                # 收集后续行作为摘要
                snippet_lines = []
                j = i + 1
                while j < len(lines) and j < i + 4:
                    next_line = lines[j]
                    if len(next_line) > 10:
                        snippet_lines.append(next_line)
                    j += 1

                snippet = " ".join(snippet_lines)[:MAX_SNIPPET_LENGTH]

                articles.append({
                    "title": line[:300],
                    "url": url,
                    "date": "",
                    "snippet": snippet,
                })
                i = j  # 跳过已处理的行
            else:
                i += 1

        logger.info("[OCR] %s: 从OCR文字中提取 %d 条", source_name, len(articles))
        return articles

    async def collect(self, source: Source) -> list[RawArticle]:
        """采集单个信息源（三级降级策略）"""
        all_articles: list[RawArticle] = []
        collected_at = datetime.utcnow().isoformat()

        for url in source.urls:
            url = url.strip().rstrip(";")
            if not url:
                continue

            try:
                # 第一步：Stealth浏览器获取
                html, screenshot = await self._fetch_page(url)

                extracted = []

                # 第二步：HTML解析
                if html:
                    extracted = extract_articles_from_html(html, url, source.name)

                # 第三步：如果HTML解析无结果但有截图，用OCR降级
                if not extracted and screenshot:
                    logger.info(
                        "[Browser] %s HTML无结果，启用截图OCR降级: %s",
                        source.name, url
                    )
                    extracted = self._ocr_extract_articles(
                        screenshot, url, source.name
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

                # 浏览器采集间隔稍长，模拟真人
                await asyncio.sleep(random.uniform(2.0, 4.0))

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
