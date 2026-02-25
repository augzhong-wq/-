"""每月汇总构建器

汇总本月所有动态，生成月度综述和趋势分析。
"""

import logging
from datetime import datetime
from calendar import monthrange
from pathlib import Path
from collections import defaultdict, Counter

from src.database.models import CuratedArticle, MonthlyReport
from src.database.store import DatabaseStore
from src.llm.client import LLMClient
from src.config.settings import DOCS_DIR, CATEGORY_ORDER, REPORT_TITLE

logger = logging.getLogger(__name__)


class MonthlyReportBuilder:
    """每月汇总构建器"""

    def __init__(self, db: DatabaseStore, llm: LLMClient):
        self.db = db
        self.llm = llm

    def build(self, target_date: str = "") -> str:
        """构建月度汇总

        Args:
            target_date: 基准日期（默认今天，取上一个月）

        Returns:
            生成的HTML文件路径
        """
        if not target_date:
            target_date = datetime.utcnow().strftime("%Y-%m-%d")

        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        # 取上一个月
        if date_obj.day == 1:
            # 如果是1号，取上个月
            if date_obj.month == 1:
                year, month = date_obj.year - 1, 12
            else:
                year, month = date_obj.year, date_obj.month - 1
        else:
            year, month = date_obj.year, date_obj.month

        _, last_day = monthrange(year, month)
        start_str = f"{year}-{month:02d}-01"
        end_str = f"{year}-{month:02d}-{last_day}"

        logger.info("构建月报: %s 至 %s", start_str, end_str)

        # 获取本月所有入选文章
        articles = self.db.get_curated_articles_by_date_range(start_str, end_str)
        if not articles:
            logger.warning("本月无入选文章，跳过月报生成")
            return ""

        # 生成月度综述
        overview = self._generate_overview(articles)

        # 生成分类统计
        category_stats = self._compute_category_stats(articles)

        # 筛选最重要的文章
        top_articles = sorted(
            articles, key=lambda a: a.importance_score, reverse=True
        )[:30]

        # 按分类分组
        categorized = self._group_by_category(top_articles)

        # 生成HTML
        output_dir = DOCS_DIR / "monthly"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{year}-{month:02d}.html"

        html = self._render(
            year, month, overview, categorized,
            category_stats, len(articles),
        )
        output_path.write_text(html, encoding="utf-8")

        # 记录到数据库
        report = MonthlyReport(
            year=year,
            month=month,
            html_path=f"monthly/{year}-{month:02d}.html",
            article_count=len(articles),
        )
        self.db.insert_monthly_report(report)

        logger.info("月报已生成: %s (%d篇)", output_path, len(articles))
        return str(output_path)

    def _generate_overview(self, articles: list[CuratedArticle]) -> str:
        """生成月度综述"""
        # 获取本月周报综述（如果有的话）
        weekly_reports = self.db.get_all_weekly_reports()
        weekly_summaries = [r.html_path for r in weekly_reports[:4]]

        # 构建简要信息
        summaries_for_llm = []
        for art in articles[:50]:
            summaries_for_llm.append(art.summary_zh[:100])

        return self.llm.generate_monthly_overview(summaries_for_llm)

    def _compute_category_stats(
        self, articles: list[CuratedArticle]
    ) -> list[tuple[str, int]]:
        """计算分类统计"""
        counter = Counter(art.category for art in articles)
        stats = [(cat, counter.get(cat, 0)) for cat in CATEGORY_ORDER if counter.get(cat, 0) > 0]
        return stats

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
        month: int,
        overview: str,
        categorized: dict[str, list[CuratedArticle]],
        category_stats: list[tuple[str, int]],
        total_articles: int,
    ) -> str:
        month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月",
                       "七月", "八月", "九月", "十月", "十一月", "十二月"]
        month_name = month_names[month] if month <= 12 else f"{month}月"

        # 统计表格
        stats_html = ""
        if category_stats:
            rows = "".join(
                f"<tr><td>{cat}</td><td>{count}</td></tr>"
                for cat, count in category_stats
            )
            stats_html = f"""
            <div class="stats-section">
                <h3 class="stats-title">本月动态分类统计</h3>
                <table class="stats-table">
                    <tr><th>分类</th><th>数量</th></tr>
                    {rows}
                    <tr class="total-row"><td><b>合计</b></td><td><b>{total_articles}</b></td></tr>
                </table>
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
            for art in categorized[cat][:5]:
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
    <title>{REPORT_TITLE} - 月报 {year}年{month_name}</title>
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
        .header-line {{ border-top: 3px solid #5B2C6F; margin-bottom: 30px; }}
        .report-title {{
            text-align: center; color: #5B2C6F; font-size: 26px;
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
            background: #f5f0fa; border-left: 4px solid #5B2C6F;
            padding: 15px 20px; margin: 20px 0;
        }}
        .overview-title {{
            color: #5B2C6F; font-size: 16px; font-weight: bold;
            margin-bottom: 10px;
        }}
        .overview-text {{ font-size: 14px; line-height: 1.8; }}
        .stats-section {{
            margin: 20px 0; padding: 15px;
            background: #fafafa; border: 1px solid #eee;
        }}
        .stats-title {{
            color: #5B2C6F; font-size: 15px; margin-bottom: 10px;
        }}
        .stats-table {{
            width: 100%; border-collapse: collapse; font-size: 14px;
        }}
        .stats-table th, .stats-table td {{
            padding: 6px 12px; text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .stats-table th {{ background: #f0f0f0; color: #555; }}
        .total-row {{ background: #f5f5f5; }}
        .section-divider {{
            border-top: 2px solid #5B2C6F; margin: 25px 0 20px;
        }}
        .category-title {{
            color: #5B2C6F; font-size: 18px; font-weight: bold;
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
            border-top: 2px solid #5B2C6F; margin-top: 30px;
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
        <h1 class="report-title">{REPORT_TITLE} · 月报</h1>
        <p class="report-subtitle">AI MONTHLY INTELLIGENCE BRIEF</p>
        <div class="report-meta">
            {year}年{month_name} &nbsp;|&nbsp; 月度综合分析
        </div>
        <div class="overview-section">
            <div class="overview-title">【月度综述】</div>
            <p class="overview-text">{overview}</p>
        </div>
        {stats_html}
        <div class="section-divider"></div>
        {categories_html}
        <div class="footer-section">
            <p class="footer-text">本月共汇集{total_articles}条动态。</p>
        </div>
    </div>
</body>
</html>"""
