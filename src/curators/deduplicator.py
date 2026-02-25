"""去重器

去重策略：
1. URL完全匹配
2. 内容哈希匹配
3. 标题相似度（Jaccard系数 > 0.8）
"""

import logging
import re
from src.database.models import RawArticle
from src.config.settings import DEDUP_SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)


class Deduplicator:
    """文章去重器"""

    def deduplicate(self, articles: list[RawArticle]) -> list[RawArticle]:
        """对文章列表进行去重

        Args:
            articles: 原始文章列表

        Returns:
            去重后的文章列表
        """
        if not articles:
            return []

        seen_urls: set[str] = set()
        seen_hashes: set[str] = set()
        seen_titles: list[str] = []
        unique_articles: list[RawArticle] = []

        for article in articles:
            # 跳过无标题文章
            if not article.title or len(article.title.strip()) < 3:
                continue

            # 跳过截图采集占位条目（这些不是真正的文章内容）
            if self._is_placeholder(article.title):
                continue

            normalized_url = self._normalize_url(article.url)

            # 1. URL去重
            if normalized_url in seen_urls:
                continue

            # 2. 内容哈希去重
            if article.content_hash and article.content_hash in seen_hashes:
                continue

            # 3. 标题相似度去重
            normalized_title = self._normalize_title(article.title)
            if self._is_similar_to_any(normalized_title, seen_titles):
                continue

            # 通过所有去重检查
            seen_urls.add(normalized_url)
            if article.content_hash:
                seen_hashes.add(article.content_hash)
            seen_titles.append(normalized_title)
            unique_articles.append(article)

        removed = len(articles) - len(unique_articles)
        if removed > 0:
            logger.info("去重完成：%d → %d（移除 %d 条重复）",
                        len(articles), len(unique_articles), removed)
        return unique_articles

    def _normalize_url(self, url: str) -> str:
        """URL标准化"""
        url = url.strip().rstrip("/").lower()
        # 移除常见追踪参数
        url = re.sub(r'[?&](utm_\w+|ref|source|campaign)=[^&]*', '', url)
        return url

    def _normalize_title(self, title: str) -> str:
        """标题标准化"""
        title = title.strip().lower()
        # 移除多余空白
        title = re.sub(r'\s+', ' ', title)
        return title

    def _is_similar_to_any(self, title: str, seen: list[str]) -> bool:
        """检查标题是否与已见列表中的任何标题相似"""
        title_words = set(title.split())
        if len(title_words) < 3:
            return False

        for seen_title in seen:
            seen_words = set(seen_title.split())
            similarity = self._jaccard_similarity(title_words, seen_words)
            if similarity >= DEDUP_SIMILARITY_THRESHOLD:
                return True
        return False

    @staticmethod
    def _is_placeholder(title: str) -> bool:
        """检查是否为占位/无效条目"""
        placeholders = [
            "截图采集", "需要人工处理", "反爬保护",
            "[截图采集]", "截图已保存", "截图已存档",
        ]
        return any(p in title for p in placeholders)

    @staticmethod
    def _jaccard_similarity(set_a: set, set_b: set) -> float:
        """计算Jaccard相似度"""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
