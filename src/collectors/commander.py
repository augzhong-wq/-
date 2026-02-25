"""采集总指挥Agent

职责：
- 指挥所有爬虫worker遍历全部渠道
- 按域名分组控制并发
- 分配HTTP或Browser采集器
- HTTP失败自动降级到Browser采集
- 汇总采集结果
- 记录采集统计
"""

import asyncio
import logging
import time
from collections import defaultdict
from urllib.parse import urlparse

from src.collectors.http_collector import HttpCollector
from src.collectors.browser_collector import BrowserCollector
from src.config.sources import get_all_sources, Source
from src.config.settings import MAX_CONCURRENCY, MAX_PER_DOMAIN
from src.database.models import RawArticle

logger = logging.getLogger(__name__)


class CollectionCommander:
    """采集总指挥 - 编排所有采集任务"""

    def __init__(self):
        self.http_collector = HttpCollector()
        self.browser_collector = BrowserCollector()
        self.stats = {
            "total_sources": 0,
            "success_sources": 0,
            "failed_sources": 0,
            "fallback_sources": 0,  # HTTP失败后降级到Browser的源数
            "total_articles": 0,
            "total_urls": 0,
            "elapsed_seconds": 0,
        }

    async def execute(self, test_mode: bool = False) -> list[RawArticle]:
        """执行采集任务

        Args:
            test_mode: 测试模式，只采集前3个源

        Returns:
            所有采集到的原始文章列表
        """
        start_time = time.time()
        sources = get_all_sources()
        if test_mode:
            sources = sources[:3]
            logger.info("=== 测试模式：仅采集前3个源 ===")

        self.stats["total_sources"] = len(sources)
        self.stats["total_urls"] = sum(len(s.urls) for s in sources)

        logger.info(
            "═══ 采集总指挥启动 ═══\n"
            "  信息源数量: %d\n"
            "  URL总数: %d\n"
            "  最大并发: %d\n"
            "  单域名并发: %d",
            len(sources), self.stats["total_urls"],
            MAX_CONCURRENCY, MAX_PER_DOMAIN
        )

        # 按采集器类型分组
        http_sources = [s for s in sources if s.collector_type == "http"]
        browser_sources = [s for s in sources if s.collector_type == "browser"]

        logger.info(
            "  HTTP采集源: %d, 浏览器采集源: %d",
            len(http_sources), len(browser_sources)
        )

        all_articles: list[RawArticle] = []
        failed_http_sources: list[Source] = []

        # 先执行HTTP采集（更快）
        if http_sources:
            http_articles, failed = await self._collect_with_concurrency(
                http_sources, self.http_collector, "HTTP"
            )
            all_articles.extend(http_articles)
            failed_http_sources = failed

        # 执行浏览器采集（已配置为browser的源）
        if browser_sources:
            browser_articles, _ = await self._collect_with_concurrency(
                browser_sources, self.browser_collector, "Browser"
            )
            all_articles.extend(browser_articles)

        # 自动降级：HTTP失败的源用Browser重试
        if failed_http_sources:
            logger.info(
                "═══ 自动降级：%d个HTTP失败源转Browser采集 ═══",
                len(failed_http_sources)
            )
            self.stats["fallback_sources"] = len(failed_http_sources)
            fallback_articles, _ = await self._collect_with_concurrency(
                failed_http_sources, self.browser_collector, "Fallback-Browser"
            )
            all_articles.extend(fallback_articles)

        # 清理资源
        await self.http_collector.close()
        await self.browser_collector.close()

        elapsed = time.time() - start_time
        self.stats["total_articles"] = len(all_articles)
        self.stats["elapsed_seconds"] = round(elapsed, 1)

        logger.info(
            "═══ 采集总指挥完成 ═══\n"
            "  成功信息源: %d/%d\n"
            "  降级采集源: %d\n"
            "  采集文章数: %d\n"
            "  耗时: %.1f秒",
            self.stats["success_sources"],
            self.stats["total_sources"],
            self.stats["fallback_sources"],
            self.stats["total_articles"],
            elapsed,
        )

        return all_articles

    async def _collect_with_concurrency(
        self,
        sources: list[Source],
        collector,
        collector_name: str,
    ) -> tuple[list[RawArticle], list[Source]]:
        """并发控制的采集

        Returns:
            (采集到的文章列表, 失败的源列表)
        """
        # 全局信号量
        global_sem = asyncio.Semaphore(MAX_CONCURRENCY)
        # 按域名的信号量
        domain_sems: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(MAX_PER_DOMAIN)
        )

        results: list[RawArticle] = []
        failed_sources: list[Source] = []
        lock = asyncio.Lock()

        async def _collect_source(source: Source):
            # 获取该源的主域名
            domain = self._get_domain(source.urls[0]) if source.urls else "unknown"
            domain_sem = domain_sems[domain]

            async with global_sem:
                async with domain_sem:
                    try:
                        articles = await collector.collect(source)
                        async with lock:
                            results.extend(articles)
                            if articles:
                                self.stats["success_sources"] += 1
                            else:
                                self.stats["failed_sources"] += 1
                                failed_sources.append(source)
                        logger.info(
                            "[%s] ✓ %s: %d 篇文章",
                            collector_name, source.name, len(articles)
                        )
                    except Exception as e:
                        async with lock:
                            self.stats["failed_sources"] += 1
                            failed_sources.append(source)
                        logger.error(
                            "[%s] ✗ %s: %s",
                            collector_name, source.name, e
                        )

        # 按优先级排序（高优先级先采集）
        sorted_sources = sorted(sources, key=lambda s: s.priority, reverse=True)

        # 创建任务
        tasks = [_collect_source(s) for s in sorted_sources]
        await asyncio.gather(*tasks, return_exceptions=True)

        return results, failed_sources

    @staticmethod
    def _get_domain(url: str) -> str:
        """获取URL的域名"""
        try:
            parsed = urlparse(url.strip().rstrip(";"))
            return parsed.netloc or "unknown"
        except Exception:
            return "unknown"

    def get_stats(self) -> dict:
        """获取采集统计"""
        return self.stats.copy()
