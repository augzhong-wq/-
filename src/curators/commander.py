"""筛选总指挥Agent

职责：
- 编排：去重 → 过滤 → 分类 → 评分
- 将筛选后的文章写入数据库
- 标记3分及以上为"建议报送"
"""

import logging
import re
import time
from datetime import datetime, timedelta

from src.curators.deduplicator import Deduplicator
from src.curators.filter import RelevanceFilter
from src.curators.classifier import ArticleClassifier
from src.curators.scorer import ImportanceScorer
from src.database.models import RawArticle, CuratedArticle
from src.database.store import DatabaseStore
from src.llm.client import LLMClient
from src.config.settings import MIN_IMPORTANCE_FOR_REPORT

# 时效性：只保留N天内的文章
FRESHNESS_DAYS = 2

logger = logging.getLogger(__name__)


class CurationCommander:
    """筛选总指挥 - 编排所有筛选任务"""

    def __init__(self, db: DatabaseStore, llm: LLMClient):
        self.db = db
        self.llm = llm
        self.deduplicator = Deduplicator()
        self.filter = RelevanceFilter(llm)
        self.classifier = ArticleClassifier(llm)
        self.scorer = ImportanceScorer(llm)
        self.stats = {
            "input_count": 0,
            "after_dedup": 0,
            "after_filter": 0,
            "after_classify": 0,
            "selected_for_report": 0,
            "stored_count": 0,
            "elapsed_seconds": 0,
        }

    def execute(self, raw_articles: list[RawArticle],
                report_date: str = "") -> list[CuratedArticle]:
        """执行筛选流程

        Args:
            raw_articles: 采集到的原始文章
            report_date: 报送日期（默认今天）

        Returns:
            筛选后的文章列表
        """
        start_time = time.time()
        if not report_date:
            report_date = datetime.utcnow().strftime("%Y-%m-%d")

        self.stats["input_count"] = len(raw_articles)
        logger.info(
            "═══ 筛选总指挥启动 ═══\n"
            "  输入文章数: %d\n"
            "  报送日期: %s",
            len(raw_articles), report_date
        )

        # 步骤1: 先存入原始文章
        stored = self.db.insert_raw_articles_batch(raw_articles)
        logger.info("步骤0: 原始文章入库 %d 篇", stored)

        # 步骤2: 去重
        deduped = self.deduplicator.deduplicate(raw_articles)
        self.stats["after_dedup"] = len(deduped)
        logger.info("步骤1: 去重 %d → %d", len(raw_articles), len(deduped))

        # 步骤2.5: 时效性过滤（只保留2天内的文章）
        fresh = self._filter_by_freshness(deduped, report_date)
        logger.info("步骤1.5: 时效性过滤 %d → %d（仅保留%d天内）",
                     len(deduped), len(fresh), FRESHNESS_DAYS)

        # 步骤3: AI相关性过滤
        filtered = self.filter.filter_articles(fresh)
        self.stats["after_filter"] = len(filtered)
        logger.info("步骤2: 过滤 %d → %d", len(deduped), len(filtered))

        # 步骤4: 分类
        classified = self.classifier.classify_articles(filtered)
        self.stats["after_classify"] = len(classified)
        logger.info("步骤3: 分类 %d 篇", len(classified))

        # 步骤5: 评分
        scored = self.scorer.score_articles(classified)
        logger.info("步骤4: 评分 %d 篇", len(scored))

        # 步骤6: 生成CuratedArticle并入库
        curated_articles = []
        for raw_art, category, score in scored:
            is_selected = score >= MIN_IMPORTANCE_FOR_REPORT
            curated = CuratedArticle(
                raw_article_id=raw_art.id or 0,
                title_zh=raw_art.title,  # 暂用原标题，摘要生成阶段再翻译
                summary_zh=raw_art.content_snippet[:200],
                category=category,
                importance_score=score,
                is_selected_for_report=is_selected,
                source_name=raw_art.source_name,
                source_url=raw_art.url,
                published_date=raw_art.published_date,
                report_date=report_date,
            )
            curated_articles.append(curated)

        # 入库
        stored_count = self.db.insert_curated_articles_batch(curated_articles)
        self.stats["stored_count"] = stored_count
        self.stats["selected_for_report"] = sum(
            1 for a in curated_articles if a.is_selected_for_report
        )

        elapsed = time.time() - start_time
        self.stats["elapsed_seconds"] = round(elapsed, 1)

        logger.info(
            "═══ 筛选总指挥完成 ═══\n"
            "  去重后: %d\n"
            "  过滤后: %d\n"
            "  入库数: %d\n"
            "  建议报送: %d\n"
            "  耗时: %.1f秒",
            self.stats["after_dedup"],
            self.stats["after_filter"],
            stored_count,
            self.stats["selected_for_report"],
            elapsed,
        )

        return [a for a in curated_articles if a.is_selected_for_report]

    def _filter_by_freshness(
        self, articles: list[RawArticle], report_date: str
    ) -> list[RawArticle]:
        """时效性过滤：只保留FRESHNESS_DAYS天内的文章

        判定逻辑：
        1. 优先用 published_date 判断
        2. published_date 不可用时，用 collected_at 判断
        3. 无法解析日期的文章默认保留（宁可多收不可漏）
        """
        try:
            ref_date = datetime.strptime(report_date, "%Y-%m-%d")
        except ValueError:
            ref_date = datetime.utcnow()

        cutoff = ref_date - timedelta(days=FRESHNESS_DAYS)
        fresh = []

        for art in articles:
            article_date = self._parse_article_date(art.published_date)
            if article_date is None:
                # 无法解析日期，用采集时间
                article_date = self._parse_article_date(art.collected_at)
            if article_date is None:
                # 完全无法判断日期，默认保留
                fresh.append(art)
                continue
            if article_date >= cutoff:
                fresh.append(art)

        removed = len(articles) - len(fresh)
        if removed > 0:
            logger.info("时效性过滤移除 %d 条过期文章（超过%d天）", removed, FRESHNESS_DAYS)
        return fresh

    @staticmethod
    def _parse_article_date(date_str: str | None) -> datetime | None:
        """尝试解析各种日期格式"""
        if not date_str or len(date_str.strip()) < 4:
            return None

        date_str = date_str.strip()

        # 常见格式
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d",
            "%d %b %Y",
            "%b %d, %Y",
            "%B %d, %Y",
            "%Y年%m月%d日",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str[:len(date_str)], fmt)
            except ValueError:
                continue

        # 尝试只取前10个字符 YYYY-MM-DD
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except ValueError:
            pass

        # 尝试用 dateutil
        try:
            from dateutil import parser as dateutil_parser
            return dateutil_parser.parse(date_str, fuzzy=True)
        except Exception:
            pass

        return None

    def get_stats(self) -> dict:
        """获取筛选统计"""
        return self.stats.copy()
