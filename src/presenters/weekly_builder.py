"""每周汇总构建器

汇总本周所有每日动态，合并同类信息，
生成周度简报。
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from src.database.models import CuratedArticle, WeeklyReport
from src.database.store import DatabaseStore
from src.llm.client import LLMClient
from src.config.settings import (
    DOCS_DIR, CATEGORY_ORDER, REPORT_TITLE
)

logger = logging.getLogger(__name__)


class WeeklyReportBuilder:
    """每周汇总构建器"""

    def __init__(self, db: DatabaseStore, llm: LLMClient):
        self.db = db
        self.llm = llm

    def build(self, target_date: str = "") -> str:
        """构建周度汇总

        Args:
            target_date: 基准日期（默认今天，向前推算本周）

        Returns:
            生成的HTML文件路径
        """
        if not target_date:
            target_date = datetime.utcnow().strftime("%Y-%m-%d")

        date_obj = datetime.strptime(target_date, "%Y-%m-%d")

        # 计算本周的起止日期（周一到周日）
        weekday = date_obj.weekday()
        week_start = date_obj - timedelta(days=weekday)
        week_end = week_start + timedelta(days=6)

        start_str = week_start.strftime("%Y-%m-%d")
        end_str = week_end.strftime("%Y-%m-%d")
        year, week_num, _ = date_obj.isocalendar()

        logger.info(
            "构建周报: %s 至 %s (第%d周)", start_str, end_str, week_num
        )

        # 获取本周所有入选文章
        articles = self.db.get_curated_articles_by_date_range(start_str, end_str)
        if not articles:
            logger.warning("本周无入选文章，跳过周报生成")
            return ""

        # 生成周度综述
        overview = self._generate_overview(articles)

        # 合并同类信息
        merged = self._merge_similar(articles)

        # 按分类分组
        categorized = self._group_by_category(merged)

        # 生成HTML
        output_dir = DOCS_DIR / "weekly"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{year}-W{week_num:02d}.html"

        html = self._render(
            year, week_num,
            week_start.strftime("%Y年%m月%d日"),
            week_end.strftime("%Y年%m月%d日"),
            overview, categorized, len(articles),
        )
        output_path.write_text(html, encoding="utf-8")

        # 记录到数据库
        report = WeeklyReport(
            week_start=start_str,
            week_end=end_str,
            year=year,
            week_number=week_num,
            html_path=f"weekly/{year}-W{week_num:02d}.html",
            article_count=len(articles),
        )
        self.db.insert_weekly_report(report)

        logger.info("周报已生成: %s (%d篇)", output_path, len(articles))
        return str(output_path)

    def _generate_overview(self, articles: list[CuratedArticle]) -> str:
        """生成周度综述"""
        daily_summaries = []
        for art in articles:
            daily_summaries.append({
                "date": art.report_date,
                "title": art.title_zh,
                "summary": art.summary_zh,
            })
        return self.llm.generate_weekly_overview(daily_summaries)

    def _merge_similar(
        self, articles: list[CuratedArticle]
    ) -> list[CuratedArticle]:
        """合并同公司/同主题的相似动态"""
        # 按来源+分类分组
        groups: dict[str, list[CuratedArticle]] = defaultdict(list)
        for art in articles:
            key = f"{art.source_name}|{art.category}"
            groups[key].append(art)

        merged = []
        for key, group in groups.items():
            if len(group) <= 2:
                merged.extend(group)
            else:
                # 保留最重要的2条，其余合并
                sorted_group = sorted(
                    group, key=lambda a: a.importance_score, reverse=True
                )
                merged.extend(sorted_group[:2])
                # 如果有多余的，合并为一条综合动态
                if len(sorted_group) > 2:
                    remaining = sorted_group[2:]
                    combined = CuratedArticle(
                        raw_article_id=0,
                        title_zh=f"{group[0].source_name}本周其他{len(remaining)}条动态",
                        summary_zh="、".join(
                            a.title_zh[:30] for a in remaining[:5]
                        ) + "等。",
                        category=group[0].category,
                        importance_score=2,
                        is_selected_for_report=True,
                        source_name=group[0].source_name,
                        source_url=group[0].source_url,
                        published_date=group[0].report_date,
                        report_date=group[0].report_date,
                    )
                    merged.append(combined)

        return merged

    def _group_by_category(
        self, articles: list[CuratedArticle]
    ) -> dict[str, list[CuratedArticle]]:
        groups: dict[str, list[CuratedArticle]] = defaultdict(list)
        for art in articles:
            groups[art.category].append(art)
        for cat in groups:
            groups[cat].sort(key=lambda a: a.importance_score, reverse=True)
        return dict(groups)

    def _render(
        self,
        year: int,
        week_num: int,
        start_display: str,
        end_display: str,
        overview: str,
        categorized: dict[str, list[CuratedArticle]],
        total_articles: int,
    ) -> str:
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
                    <div class="article-meta">来源：{art.source_name}</div>
                </div>"""

            categories_html += f"""
            <div class="category-section">
                <h2 class="category-title">{num_str}、{cat}</h2>
                <div class="category-divider"></div>
                {articles_html}
            </div>"""

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{REPORT_TITLE} - 周报 {year}年第{week_num}周</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "SimSun", "宋体", "Microsoft YaHei", serif;
            background: #f5f5f5; color: #333; line-height: 1.8;
        }}
        .container {{
            max-width: 800px; margin: 20px auto; background: #fff;
            padding: 40px 50px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .header-line {{ border-top: 3px solid #003366; margin-bottom: 30px; }}
        .report-title {{
            text-align: center; color: #003366; font-size: 26px;
            font-weight: bold; letter-spacing: 3px; margin-bottom: 5px;
        }}
        .report-subtitle {{
            text-align: center; color: #666; font-size: 13px;
            margin-bottom: 15px;
        }}
        .report-meta {{
            text-align: center; color: #555; font-size: 14px;
            margin-bottom: 20px; padding-bottom: 15px;
            border-bottom: 1px solid #ddd;
        }}
        .overview-section {{
            background: #f0f4f8; border-left: 4px solid #003366;
            padding: 15px 20px; margin: 20px 0;
        }}
        .overview-title {{
            color: #003366; font-size: 16px; font-weight: bold;
            margin-bottom: 10px;
        }}
        .overview-text {{ font-size: 14px; line-height: 1.8; }}
        .section-divider {{
            border-top: 2px solid #003366; margin: 25px 0 20px;
        }}
        .category-title {{
            color: #003366; font-size: 18px; font-weight: bold;
            margin-bottom: 5px;
        }}
        .category-divider {{
            border-top: 1px solid #ccc; margin-bottom: 15px;
        }}
        .article-item {{
            margin-bottom: 15px; padding-bottom: 12px;
            border-bottom: 1px dotted #e0e0e0;
        }}
        .article-item:last-child {{ border-bottom: none; }}
        .importance {{ color: #DAA520; font-size: 13px; margin-right: 5px; }}
        .article-title {{
            font-weight: bold; color: #003366; font-size: 15px;
        }}
        .article-summary {{
            font-size: 14px; color: #444; line-height: 1.7;
            margin: 5px 0; text-indent: 2em;
        }}
        .article-meta {{ font-size: 12px; color: #999; }}
        .footer-section {{
            border-top: 2px solid #003366; margin-top: 30px;
            padding-top: 15px;
        }}
        .footer-text {{ font-size: 13px; color: #666; }}
        @media (max-width: 600px) {{
            .container {{ padding: 20px 15px; margin: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-line"></div>
        <h1 class="report-title">{REPORT_TITLE} · 周报</h1>
        <p class="report-subtitle">AI WEEKLY INTELLIGENCE BRIEF</p>
        <div class="report-meta">
            {year}年第{week_num}周 &nbsp;|&nbsp; {start_display} — {end_display}
        </div>
        <div class="overview-section">
            <div class="overview-title">【本周综述】</div>
            <p class="overview-text">{overview}</p>
        </div>
        <div class="section-divider"></div>
        {categories_html}
        <div class="footer-section">
            <p class="footer-text">
                本周共汇集{total_articles}条动态。
            </p>
        </div>
    </div>
</body>
</html>"""
