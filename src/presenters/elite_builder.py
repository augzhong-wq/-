"""每日精选报送构建器

面向高层领导的精选版简报。
每个分类原则上不超过5条，只保留真正值得领导关注的重大事件。

版式特点：
- 比日报更精炼，一页纸内快速获取核心信息
- 金色主色调，体现"精选"定位
- 每条动态2-3行，极度精炼
"""

import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from src.database.models import CuratedArticle
from src.database.store import DatabaseStore
from src.llm.client import LLMClient
from src.config.settings import DOCS_DIR, CATEGORY_ORDER

logger = logging.getLogger(__name__)

WEEKDAY_MAP = {
    0: "星期一", 1: "星期二", 2: "星期三",
    3: "星期四", 4: "星期五", 5: "星期六", 6: "星期日",
}


class EliteReportBuilder:
    """每日精选报送构建器"""

    def __init__(self, db: DatabaseStore, llm: LLMClient):
        self.db = db
        self.llm = llm

    def build(
        self,
        articles: list[CuratedArticle],
        report_date: str = "",
        collection_stats: dict | None = None,
    ) -> str:
        """构建每日精选报送

        Args:
            articles: 所有入选简报的文章（已有摘要）
            report_date: 报告日期
            collection_stats: 采集统计

        Returns:
            生成的HTML文件路径
        """
        if not report_date:
            report_date = datetime.utcnow().strftime("%Y-%m-%d")

        logger.info("开始构建每日精选报送 (%s)，候选 %d 篇", report_date, len(articles))

        # 第一步：用LLM进行精选筛选
        elite_articles = self._screen_elite(articles)
        logger.info("精选筛选完成：%d → %d 篇", len(articles), len(elite_articles))

        if not elite_articles:
            logger.warning("无文章入选精选报送")
            return ""

        # 第二步：按分类分组
        categorized = self._group_by_category(elite_articles)

        # 第三步：生成要点
        highlights = self._generate_highlights(elite_articles)

        # 第四步：生成HTML
        date_obj = datetime.strptime(report_date, "%Y-%m-%d")
        date_display = date_obj.strftime("%Y年%m月%d日")
        weekday = WEEKDAY_MAP.get(date_obj.weekday(), "")
        epoch = datetime(2026, 1, 1)
        issue_number = (date_obj - epoch).days + 1

        output_dir = DOCS_DIR / "elite"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{report_date}.html"

        html = self._render(
            date_display, weekday, issue_number, report_date,
            categorized, highlights, len(elite_articles),
            collection_stats or {},
        )
        output_path.write_text(html, encoding="utf-8")

        logger.info("每日精选报送已生成: %s (%d篇)", output_path, len(elite_articles))
        return str(output_path)

    def _screen_elite(self, articles: list[CuratedArticle]) -> list[CuratedArticle]:
        """用LLM进行精选筛选"""
        # 准备数据
        article_dicts = []
        for art in articles:
            article_dicts.append({
                "title_zh": art.title_zh,
                "summary_zh": art.summary_zh,
                "category": art.category,
                "importance_score": art.importance_score,
                "source_name": art.source_name,
                "source_url": art.source_url,
            })

        # 调用LLM精选
        screened = self.llm.screen_elite_picks(article_dicts, max_per_category=5)

        # 筛选入选文章
        elite = []
        for i, art_dict in enumerate(screened):
            if art_dict.get("is_elite", False):
                elite.append(articles[i])

        # 如果LLM精选太少，补充4-5分的文章
        if len(elite) < 5:
            for art in articles:
                if art not in elite and art.importance_score >= 4:
                    elite.append(art)

        return elite

    def _group_by_category(
        self, articles: list[CuratedArticle]
    ) -> dict[str, list[CuratedArticle]]:
        groups: dict[str, list[CuratedArticle]] = defaultdict(list)
        for art in articles:
            groups[art.category].append(art)
        for cat in groups:
            groups[cat].sort(key=lambda a: a.importance_score, reverse=True)
        return dict(groups)

    def _generate_highlights(self, articles: list[CuratedArticle]) -> list[str]:
        """生成精选要点"""
        top = sorted(articles, key=lambda a: a.importance_score, reverse=True)[:5]

        if not self.llm.is_available:
            return [f"▸ {a.title_zh}" for a in top]

        system_prompt = (
            "你是面向国家高层领导的AI简报总编辑。请提炼3-5条核心要点。\n"
            "要求：\n"
            "- 每条一句话，15-30字，陈述事件本质和影响\n"
            "- 每条以'▸'开头，直接输出\n"
            "- 语言严谨、正式、平实，参照新华社通稿风格\n"
            "- 禁止感叹号、网络用语、夸张修辞、标题党词汇\n"
            "- 禁止'震撼''炸裂''最强''来了''太强了'等用语"
        )
        articles_text = "\n".join(
            f"- [{a.source_name}] {a.title_zh}: {a.summary_zh[:80]}"
            for a in top
        )
        response = self.llm.chat(system_prompt, articles_text, temperature=0.2)
        if response:
            return [
                line.strip() for line in response.strip().split("\n")
                if line.strip() and len(line.strip()) > 5
            ][:5]
        return [f"▸ {a.title_zh}" for a in top]

    def _render(
        self,
        date_display: str,
        weekday: str,
        issue_number: int,
        report_date: str,
        categorized: dict[str, list[CuratedArticle]],
        highlights: list[str],
        article_count: int,
        collection_stats: dict,
    ) -> str:
        # 要点
        highlights_html = ""
        if highlights:
            items = "\n".join(f"<li>{h}</li>" for h in highlights)
            highlights_html = f"""
            <div class="highlights-section">
                <h2 class="highlights-title">【今日要闻】</h2>
                <ul class="highlights-list">{items}</ul>
            </div>"""

        # 分类内容
        categories_html = ""
        section_num = 0
        nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
        for cat in CATEGORY_ORDER:
            if cat not in categorized:
                continue
            section_num += 1
            num_str = nums[section_num - 1] if section_num <= 10 else str(section_num)

            articles_html = ""
            for art in categorized[cat]:
                stars = "★" * art.importance_score
                articles_html += f"""
                <div class="article-item">
                    <div class="article-header">
                        <span class="importance">{stars}</span>
                        <span class="article-title">{art.title_zh}</span>
                    </div>
                    <p class="article-summary">{art.summary_zh}</p>
                    <div class="article-meta">
                        来源：{art.source_name}
                        <a href="{art.source_url}" target="_blank" class="source-link">[原文]</a>
                    </div>
                </div>"""

            categories_html += f"""
            <div class="category-section">
                <h2 class="category-title">{num_str}、{cat}（{len(categorized[cat])}条）</h2>
                <div class="category-divider"></div>
                {articles_html}
            </div>"""

        source_count = collection_stats.get("success_sources", 0)
        total_collected = collection_stats.get("total_articles", 0)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI动态精选报送 - {date_display}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "SimSun", "宋体", "Microsoft YaHei", serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.8;
        }}
        .container {{
            max-width: 800px;
            margin: 20px auto;
            background: #fff;
            padding: 40px 50px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .header-line {{
            border-top: 4px solid #B8860B;
            margin-bottom: 25px;
        }}
        .badge {{
            text-align: center;
            margin-bottom: 10px;
        }}
        .badge span {{
            display: inline-block;
            background: #B8860B;
            color: #fff;
            font-size: 12px;
            padding: 2px 16px;
            letter-spacing: 3px;
        }}
        .report-title {{
            text-align: center;
            color: #8B0000;
            font-size: 26px;
            font-weight: bold;
            letter-spacing: 4px;
            margin-bottom: 5px;
        }}
        .report-subtitle {{
            text-align: center;
            color: #B8860B;
            font-size: 13px;
            letter-spacing: 2px;
            margin-bottom: 12px;
        }}
        .report-meta {{
            text-align: center;
            color: #555;
            font-size: 14px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid #ddd;
        }}
        .highlights-section {{
            background: #fffdf0;
            border-left: 4px solid #B8860B;
            padding: 15px 20px;
            margin: 15px 0 20px;
        }}
        .highlights-title {{
            color: #B8860B;
            font-size: 16px;
            margin-bottom: 8px;
        }}
        .highlights-list {{
            list-style: none;
            padding: 0;
        }}
        .highlights-list li {{
            padding: 3px 0;
            font-size: 14px;
            line-height: 1.6;
            font-weight: bold;
            color: #333;
        }}
        .section-divider {{
            border-top: 2px solid #B8860B;
            margin: 20px 0 15px;
        }}
        .category-title {{
            color: #8B0000;
            font-size: 17px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .category-divider {{
            border-top: 1px solid #ddd;
            margin-bottom: 12px;
        }}
        .article-item {{
            margin-bottom: 15px;
            padding-bottom: 12px;
            border-bottom: 1px dotted #e0e0e0;
        }}
        .article-item:last-child {{ border-bottom: none; }}
        .article-header {{ margin-bottom: 4px; }}
        .importance {{ color: #B8860B; font-size: 13px; margin-right: 5px; }}
        .article-title {{
            font-weight: bold;
            color: #003366;
            font-size: 15px;
        }}
        .article-summary {{
            font-size: 14px;
            color: #444;
            line-height: 1.7;
            margin: 4px 0;
            text-indent: 2em;
        }}
        .article-meta {{
            font-size: 12px;
            color: #999;
        }}
        .source-link {{
            color: #003366;
            text-decoration: none;
            margin-left: 5px;
        }}
        .source-link:hover {{ text-decoration: underline; }}
        .footer-section {{
            border-top: 2px solid #B8860B;
            margin-top: 25px;
            padding-top: 12px;
        }}
        .footer-title {{
            color: #B8860B;
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .footer-text {{
            font-size: 12px;
            color: #888;
            line-height: 1.6;
        }}
        @media (max-width: 600px) {{
            .container {{ padding: 20px 15px; margin: 10px; }}
            .report-title {{ font-size: 22px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-line"></div>
        <div class="badge"><span>精 选 报 送</span></div>
        <h1 class="report-title">AI动态精选报送</h1>
        <p class="report-subtitle">ELITE AI INTELLIGENCE BRIEF</p>
        <div class="report-meta">
            {date_display} {weekday} &nbsp;&nbsp; 第{issue_number:03d}期
        </div>
        {highlights_html}
        <div class="section-divider"></div>
        {categories_html}
        <div class="footer-section">
            <div class="footer-title">【编辑说明】</div>
            <p class="footer-text">
                本期从{source_count}个信息源、{total_collected}条动态中精选{article_count}条报送。
                每类原则上不超过5条，仅保留具有行业广泛影响的重大事件。
            </p>
        </div>
    </div>
</body>
</html>"""
