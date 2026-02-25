"""重要性评分器

面向高层领导的评分体系。领导关注的不是个别技术细节，
而是对国际社会、AI产业、国家政策产生广泛影响的重大事件。

评分维度（领导视角）：
1. 行业影响力 — 是否引起业界广泛关注，而非仅在学术圈
2. 企业量级 — 是否涉及头部企业（OpenAI/Google/NVIDIA等）的重大动作
3. 产品/技术里程碑 — 是否是标志性产品发布或技术突破（非普通论文）
4. 政策/监管 — 是否是主要国家（美、欧、英、中）的重大AI政策或法案
5. 投融资规模 — 是否是大额（10亿+）或标志性融资
6. 重要人物言论 — 是否涉及马斯克、奥特曼、黄仁勋、扎克伯格等关键人物
7. 战略报告 — 是否是权威机构发布的重大行业报告
"""

import logging

from src.database.models import RawArticle
from src.llm.client import LLMClient

logger = logging.getLogger(__name__)

# 头部企业/机构（涉及即加权）
TIER1_SOURCES = {
    "OpenAI", "Alphabet/Google", "Microsoft", "Meta", "Apple",
    "NVIDIA", "Anthropic", "xAI", "Mistral AI",
}

# 重大政策/监管来源（涉及即加权）
POLICY_SOURCES = {
    "白宫OSTP", "NIST", "BIS", "FTC", "DOJ",
    "欧盟AI Office", "EU AI Act", "DSIT",
    "CHIPS.gov", "CRS", "GAO",
}

# 权威智库/媒体（发布重大报告时加权）
AUTHORITY_SOURCES = {
    "Stanford HAI", "MIT Technology Review",
    "布鲁金斯学会", "麦肯锡", "Goldman Sachs AI研究",
    "RAND Corporation", "Georgetown CSET", "CNAS",
    "CB Insights",
}

# 重要人物关键词（标题/摘要中出现即加权）
KEY_FIGURES = [
    "elon musk", "马斯克", "sam altman", "奥特曼", "altman",
    "jensen huang", "黄仁勋", "huang",
    "satya nadella", "纳德拉", "nadella",
    "sundar pichai", "皮查伊", "pichai",
    "mark zuckerberg", "扎克伯格", "zuckerberg",
    "tim cook", "库克",
    "dario amodei", "amodei",
    "demis hassabis", "哈萨比斯", "hassabis",
    "fei-fei li", "李飞飞",
    "andrew ng", "吴恩达",
    "geoffrey hinton", "辛顿", "hinton",
    "yann lecun", "lecun",
    "ilya sutskever", "sutskever",
]

# 重大事件关键词（标题中出现即加权）
MAJOR_EVENT_KEYWORDS = [
    # 重大动作
    "launch", "release", "announce", "unveil", "introduce",
    "发布", "推出", "发布会", "上线",
    # 重大规模
    "billion", "亿", "万亿", "trillion",
    # 政策法规
    "executive order", "行政令", "legislation", "法案", "regulation",
    "ban", "禁令", "sanction", "制裁", "tariff", "关税",
    "act", "law", "directive", "指令",
    # 里程碑
    "breakthrough", "突破", "milestone", "里程碑",
    "first", "首次", "record", "纪录",
    "ipo", "acquisition", "收购", "merger", "合并",
    # 战略
    "partnership", "合作", "alliance", "联盟",
    "strategy", "战略", "roadmap", "路线图",
]


class ImportanceScorer:
    """面向高层领导的重要性评分器"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def score_articles(
        self, articles: list[tuple[RawArticle, str]]
    ) -> list[tuple[RawArticle, str, int]]:
        """对文章进行重要性评分（领导视角）"""
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

        # 调用LLM评分（使用优化后的领导视角prompt）
        result_dicts = self.llm.score_importance(article_dicts)

        # 组合结果，叠加规则加权
        results = []
        for i, art_dict in enumerate(result_dicts):
            art, cat = articles[i]
            base_score = art_dict.get("importance_score", 3)

            # 规则加权
            bonus = self._compute_bonus(art)
            final_score = min(base_score + bonus, 5)

            results.append((art, cat, final_score))

        # 统计评分分布
        score_dist = {}
        for _, _, score in results:
            score_dist[score] = score_dist.get(score, 0) + 1
        logger.info("评分完成 (%d篇)：%s", len(results), score_dist)

        return results

    def _compute_bonus(self, article: RawArticle) -> int:
        """基于规则的加分"""
        bonus = 0
        title_lower = article.title.lower()
        snippet_lower = (article.content_snippet or "").lower()
        text = f"{title_lower} {snippet_lower}"

        # 来自头部企业 +1
        if article.source_name in TIER1_SOURCES:
            bonus += 1

        # 来自政策/监管机构 +1
        if article.source_name in POLICY_SOURCES:
            bonus += 1

        # 标题涉及重要人物 +1
        if any(fig in text for fig in KEY_FIGURES):
            bonus += 1

        # 标题涉及重大事件关键词 +1（至少匹配2个才加分，避免误判）
        major_matches = sum(1 for kw in MAJOR_EVENT_KEYWORDS if kw in text)
        if major_matches >= 2:
            bonus += 1

        return min(bonus, 2)  # 最多加2分，避免过度加权
