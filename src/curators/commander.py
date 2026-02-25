"""筛选总指挥Agent

职责：
- 编排：去重 → 过滤 → 分类 → 评分
- 将筛选后的文章写入数据库
- 标记3分及以上为"建议报送"
"""

import logging
import time
from datetime import datetime

from src.curators.deduplicator import Deduplicator
from src.curators.filter import RelevanceFilter
from src.curators.classifier import ArticleClassifier
from src.curators.scorer import ImportanceScorer
from src.database.models import RawArticle, CuratedArticle
from src.database.store import DatabaseStore
from src.llm.client import LLMClient
from src.config.settings import MIN_IMPORTANCE_FOR_REPORT

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

        # 步骤3: AI相关性过滤
        filtered = self.filter.filter_articles(deduped)
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

    def get_stats(self) -> dict:
        """获取筛选统计"""
        return self.stats.copy()
