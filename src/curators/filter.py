"""相关性过滤器

使用LLM判断文章是否与AI相关，
并提供关键词降级方案。
"""

import logging

from src.database.models import RawArticle
from src.llm.client import LLMClient

logger = logging.getLogger(__name__)


class RelevanceFilter:
    """AI相关性过滤器"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def filter_articles(self, articles: list[RawArticle]) -> list[RawArticle]:
        """过滤出与AI相关的文章

        Args:
            articles: 原始文章列表

        Returns:
            AI相关的文章列表
        """
        if not articles:
            return []

        # 准备LLM输入
        article_dicts = []
        for i, art in enumerate(articles):
            article_dicts.append({
                "title": art.title,
                "snippet": art.content_snippet,
                "index": i,
            })

        # 调用LLM进行相关性判断
        result_dicts = self.llm.filter_relevance(article_dicts)

        # 筛选相关文章
        relevant = []
        for i, art_dict in enumerate(result_dicts):
            if art_dict.get("is_relevant", True):  # 默认为相关
                relevant.append(articles[i])

        filtered_count = len(articles) - len(relevant)
        logger.info(
            "相关性过滤：%d → %d（过滤 %d 条无关内容）",
            len(articles), len(relevant), filtered_count
        )
        return relevant
