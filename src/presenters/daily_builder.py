"""每日简报构建器

从数据库获取当日入选文章，
按分类分组、按重要性排序，
使用Jinja2渲染HTML简报。
"""

import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from jinja2 import Environment, FileSystemLoader

from src.database.models import CuratedArticle, DailyReport
from src.database.store import DatabaseStore
from src.config.settings import (
    DOCS_DIR, TEMPLATES_DIR, CATEGORY_ORDER,
    REPORT_TITLE, REPORT_SUBTITLE
)

logger = logging.getLogger(__name__)

# 中文星期映射
WEEKDAY_MAP = {
    0: "星期一", 1: "星期二", 2: "星期三",
    3: "星期四", 4: "星期五", 5: "星期六", 6: "星期日",
}


class DailyReportBuilder:
    """每日简报构建器"""

    def __init__(self, db: DatabaseStore):
        self.db = db
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )

    def build(
        self,
        articles: list[CuratedArticle],
        report_date: str = "",
        highlights: list[str] | None = None,
        collection_stats: dict | None = None,
        curation_stats: dict | None = None,
    ) -> str:
        """构建每日简报HTML

        Args:
            articles: 入选简报的文章列表
            report_date: 报告日期 YYYY-MM-DD
            highlights: 本期要点列表
            collection_stats: 采集统计
            curation_stats: 筛选统计

        Returns:
            生成的HTML文件路径
        """
        if not report_date:
            report_date = datetime.utcnow().strftime("%Y-%m-%d")

        # 解析日期
        date_obj = datetime.strptime(report_date, "%Y-%m-%d")
        date_display = date_obj.strftime("%Y年%m月%d日")
        weekday = WEEKDAY_MAP.get(date_obj.weekday(), "")

        # 计算期号（从2026年1月1日起算）
        epoch = datetime(2026, 1, 1)
        issue_number = (date_obj - epoch).days + 1

        # 按分类分组
        categorized = self._group_by_category(articles)

        # 确保输出目录存在
        output_dir = DOCS_DIR / "daily"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{report_date}.html"

        # 渲染模板
        try:
            template = self.env.get_template("daily.html")
        except Exception:
            # 如果模板不存在，使用内置模板
            html = self._render_builtin(
                date_display, weekday, issue_number,
                categorized, highlights or [],
                collection_stats or {}, curation_stats or {},
                len(articles), report_date,
            )
            output_path.write_text(html, encoding="utf-8")
            logger.info("每日简报已生成（内置模板）: %s", output_path)
        else:
            html = template.render(
                title=REPORT_TITLE,
                subtitle=REPORT_SUBTITLE,
                date_display=date_display,
                weekday=weekday,
                issue_number=issue_number,
                report_date=report_date,
                categories=categorized,
                category_order=CATEGORY_ORDER,
                highlights=highlights or [],
                collection_stats=collection_stats or {},
                curation_stats=curation_stats or {},
                article_count=len(articles),
                generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            )
            output_path.write_text(html, encoding="utf-8")
            logger.info("每日简报已生成: %s", output_path)

        # 记录到数据库
        daily_report = DailyReport(
            report_date=report_date,
            html_path=f"daily/{report_date}.html",
            article_count=len(articles),
            source_count=collection_stats.get("success_sources", 0) if collection_stats else 0,
            total_collected=collection_stats.get("total_articles", 0) if collection_stats else 0,
        )
        self.db.insert_daily_report(daily_report)

        return str(output_path)

    def _group_by_category(
        self, articles: list[CuratedArticle]
    ) -> dict[str, list[CuratedArticle]]:
        """按分类分组，每组内按重要性排序"""
        groups: dict[str, list[CuratedArticle]] = defaultdict(list)
        for art in articles:
            groups[art.category].append(art)

        # 每组内按重要性排序
        for cat in groups:
            groups[cat].sort(key=lambda a: a.importance_score, reverse=True)

        return dict(groups)

    def _render_builtin(
        self,
        date_display: str,
        weekday: str,
        issue_number: int,
        categorized: dict[str, list[CuratedArticle]],
        highlights: list[str],
        collection_stats: dict,
        curation_stats: dict,
        article_count: int,
        report_date: str,
    ) -> str:
        """使用内置HTML模板（备用方案）"""
        # 构建分类HTML
        categories_html = ""
        section_num = 0
        for cat in CATEGORY_ORDER:
            if cat not in categorized:
                continue
            section_num += 1
            nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
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
                        来源：{art.source_name} | {art.published_date or report_date}
                        <a href="{art.source_url}" target="_blank" class="source-link">[原文]</a>
                    </div>
                </div>"""

            categories_html += f"""
            <div class="category-section">
                <h2 class="category-title">{num_str}、{cat}</h2>
                <div class="category-divider"></div>
                {articles_html}
            </div>"""

        # 要点HTML
        highlights_html = ""
        if highlights:
            items = "\n".join(f"<li>{h}</li>" for h in highlights)
            highlights_html = f"""
            <div class="highlights-section">
                <h2 class="highlights-title">【本期要点】</h2>
                <ul class="highlights-list">{items}</ul>
            </div>"""

        source_count = collection_stats.get("success_sources", 0)
        total_collected = collection_stats.get("total_articles", 0)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{REPORT_TITLE} - {date_display}</title>
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
        .header-line {{ border-top: 3px solid #8B0000; margin-bottom: 30px; }}
        .report-title {{
            text-align: center;
            color: #8B0000;
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 4px;
            margin-bottom: 5px;
        }}
        .report-subtitle {{
            text-align: center;
            color: #666;
            font-size: 13px;
            letter-spacing: 2px;
            margin-bottom: 15px;
        }}
        .report-meta {{
            text-align: center;
            color: #555;
            font-size: 14px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #ddd;
        }}
        .highlights-section {{
            background: #fdf6f0;
            border-left: 4px solid #8B0000;
            padding: 15px 20px;
            margin: 20px 0;
        }}
        .highlights-title {{
            color: #8B0000;
            font-size: 16px;
            margin-bottom: 10px;
        }}
        .highlights-list {{
            list-style: none;
            padding: 0;
        }}
        .highlights-list li {{
            padding: 4px 0;
            font-size: 14px;
            line-height: 1.6;
        }}
        .section-divider {{
            border-top: 2px solid #8B0000;
            margin: 25px 0 20px;
        }}
        .category-title {{
            color: #8B0000;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .category-divider {{
            border-top: 1px solid #ccc;
            margin-bottom: 15px;
        }}
        .article-item {{
            margin-bottom: 18px;
            padding-bottom: 15px;
            border-bottom: 1px dotted #e0e0e0;
        }}
        .article-item:last-child {{ border-bottom: none; }}
        .article-header {{
            margin-bottom: 5px;
        }}
        .importance {{
            color: #DAA520;
            font-size: 13px;
            margin-right: 5px;
        }}
        .article-title {{
            font-weight: bold;
            color: #003366;
            font-size: 15px;
        }}
        .article-summary {{
            font-size: 14px;
            color: #444;
            line-height: 1.7;
            margin: 5px 0;
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
            border-top: 2px solid #8B0000;
            margin-top: 30px;
            padding-top: 15px;
        }}
        .footer-title {{
            color: #8B0000;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        .footer-text {{
            font-size: 13px;
            color: #666;
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
        <h1 class="report-title">{REPORT_TITLE}</h1>
        <p class="report-subtitle">{REPORT_SUBTITLE}</p>
        <div class="report-meta">
            {date_display} {weekday} &nbsp;&nbsp; 第{issue_number:03d}期
        </div>
        {highlights_html}
        <div class="section-divider"></div>
        {categories_html}
        <div class="footer-section">
            <div class="footer-title">【编辑说明】</div>
            <p class="footer-text">
                本期共监测{source_count}个信息源，采集{total_collected}条动态，
                精选{article_count}条报送。数据采集时间：北京时间15:00。
            </p>
        </div>
    </div>
</body>
</html>"""
