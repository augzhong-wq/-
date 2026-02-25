"""分类器

将文章分入预定义的10大类别。
"""

import logging

from src.database.models import RawArticle
from src.llm.client import LLMClient
from src.config.settings import CATEGORIES

logger = logging.getLogger(__name__)


class ArticleClassifier:
    """文章分类器"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def classify_articles(
        self, articles: list[RawArticle]
    ) -> list[tuple[RawArticle, str]]:
        """对文章进行分类

        Args:
            articles: 文章列表

        Returns:
            [(article, category), ...] 元组列表
        """
        if not articles:
            return []

        # 准备LLM输入
        article_dicts = []
        for i, art in enumerate(articles):
            article_dicts.append({
                "title": art.title,
                "snippet": art.content_snippet,
                "source": art.source_name,
                "index": i,
            })

        # 调用LLM分类
        result_dicts = self.llm.classify_articles(article_dicts)

        # 组合结果
        results = []
        valid_categories = set(CATEGORIES.keys())
        for i, art_dict in enumerate(result_dicts):
            category = art_dict.get("category", "企业动态")
            # 验证分类有效性
            if category not in valid_categories:
                category = self._guess_category(articles[i])
            results.append((articles[i], category))

        # 统计分类分布
        cat_counts = {}
        for _, cat in results:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        logger.info("分类完成 (%d篇)：%s", len(results), cat_counts)

        return results

    def _guess_category(self, article: RawArticle) -> str:
        """根据信息源类别推断文章分类"""
        source_to_category = {
            "AI芯片公司": "芯片与算力",
            "AI龙头企业": "企业动态",
            "新兴AI独角兽": "企业动态",
            "高校": "研究前沿",
            "学术期刊": "研究前沿",
            "欧洲研究机构": "研究前沿",
            "加拿大AI生态": "研究前沿",
            "学者言论": "研究前沿",
            "官网/社媒": "研究前沿",
            "科技与商业媒体": "企业动态",
            "中文快速聚合": "企业动态",
            "智库与咨询机构": "行业应用",
            "年度战略报告": "行业应用",
            "战略分析平台": "芯片与算力",
            "安全评测": "安全伦理",
            "投融资分析": "投融资",
            "PR新闻通讯社": "企业动态",
            "生态大会": "产品发布",
            "国际AI安全机构": "政策监管",
            "美国政策来源": "政策监管",
            "欧盟政策来源": "政策监管",
            "英国政策来源": "政策监管",
            "AI政策智库": "政策监管",
            "国际组织AI治理": "政策监管",
            "专利数据库": "技术突破",
            "人才市场": "人才市场",
        }
        return source_to_category.get(article.source_sub_category, "企业动态")
