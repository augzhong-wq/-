"""重要性评分器

5级评分体系，结合LLM评分和规则加权。
"""

import logging

from src.database.models import RawArticle
from src.llm.client import LLMClient

logger = logging.getLogger(__name__)

# 高优先级信息源（自动+1分）
HIGH_PRIORITY_SOURCES = {
    "OpenAI", "Alphabet/Google", "Microsoft", "Meta", "Apple",
    "NVIDIA", "Anthropic", "xAI",
    "白宫OSTP", "NIST", "BIS", "FTC", "DOJ",
    "欧盟AI Office", "EU AI Act", "DSIT",
    "Stanford HAI", "MIT Technology Review",
}


class ImportanceScorer:
    """重要性评分器"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def score_articles(
        self, articles: list[tuple[RawArticle, str]]
    ) -> list[tuple[RawArticle, str, int]]:
        """对文章进行重要性评分

        Args:
            articles: [(article, category), ...]

        Returns:
            [(article, category, score), ...]
        """
        if not articles:
            return []

        # 准备LLM输入
        article_dicts = []
        for i, (art, cat) in enumerate(articles):
            article_dicts.append({
                "title": art.title,
                "snippet": art.content_snippet,
                "source": art.source_name,
                "category": cat,
                "index": i,
            })

        # 调用LLM评分
        result_dicts = self.llm.score_importance(article_dicts)

        # 组合结果，叠加规则加权
        results = []
        for i, art_dict in enumerate(result_dicts):
            art, cat = articles[i]
            base_score = art_dict.get("importance_score", 3)

            # 规则加权：高优先级来源 +1
            if art.source_name in HIGH_PRIORITY_SOURCES:
                base_score = min(base_score + 1, 5)

            results.append((art, cat, base_score))

        # 统计评分分布
        score_dist = {}
        for _, _, score in results:
            score_dist[score] = score_dist.get(score, 0) + 1
        logger.info("评分完成 (%d篇)：%s", len(results), score_dist)

        return results
