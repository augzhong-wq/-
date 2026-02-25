"""呈现总指挥Agent

职责：
- 精编摘要生成
- 构建每日/每周/每月简报
- 更新归档索引页
"""

import logging
import time
from datetime import datetime
from pathlib import Path

from src.presenters.summarizer import Summarizer
from src.presenters.daily_builder import DailyReportBuilder
from src.presenters.elite_builder import EliteReportBuilder
from src.presenters.weekly_builder import WeeklyReportBuilder
from src.presenters.monthly_builder import MonthlyReportBuilder
from src.database.models import CuratedArticle
from src.database.store import DatabaseStore
from src.llm.client import LLMClient
from src.config.settings import DOCS_DIR, REPORT_TITLE

logger = logging.getLogger(__name__)


class PresentationCommander:
    """呈现总指挥 - 编排所有呈现任务"""

    def __init__(self, db: DatabaseStore, llm: LLMClient):
        self.db = db
        self.llm = llm
        self.summarizer = Summarizer(llm)
        self.daily_builder = DailyReportBuilder(db)
        self.elite_builder = EliteReportBuilder(db, llm)
        self.weekly_builder = WeeklyReportBuilder(db, llm)
        self.monthly_builder = MonthlyReportBuilder(db, llm)

    def execute_daily(
        self,
        articles: list[CuratedArticle],
        report_date: str = "",
        collection_stats: dict | None = None,
        curation_stats: dict | None = None,
    ) -> str:
        """执行每日简报生成

        Args:
            articles: 入选简报的文章
            report_date: 报告日期
            collection_stats: 采集统计
            curation_stats: 筛选统计

        Returns:
            生成的HTML文件路径
        """
        start_time = time.time()
        if not report_date:
            report_date = datetime.utcnow().strftime("%Y-%m-%d")

        logger.info(
            "═══ 呈现总指挥启动（日报）═══\n"
            "  文章数: %d\n"
            "  报送日期: %s",
            len(articles), report_date
        )

        # 步骤1: 生成精编摘要
        articles = self.summarizer.generate_summaries(articles)
        logger.info("步骤1: 精编摘要生成完成")

        # 步骤2: 生成本期要点
        highlights = self.summarizer.generate_highlights(articles)
        logger.info("步骤2: 本期要点: %s", highlights)

        # 步骤3: 构建日报HTML
        html_path = self.daily_builder.build(
            articles=articles,
            report_date=report_date,
            highlights=highlights,
            collection_stats=collection_stats,
            curation_stats=curation_stats,
        )
        logger.info("步骤3: 日报HTML生成: %s", html_path)

        # 步骤4: 构建每日精选报送
        elite_path = self.elite_builder.build(
            articles=articles,
            report_date=report_date,
            collection_stats=collection_stats,
        )
        logger.info("步骤4: 精选报送生成: %s", elite_path)

        # 步骤5: 更新索引页
        self._update_index()
        logger.info("步骤5: 索引页已更新")

        elapsed = time.time() - start_time
        logger.info(
            "═══ 呈现总指挥完成（日报）═══\n"
            "  输出文件: %s\n"
            "  耗时: %.1f秒",
            html_path, elapsed
        )

        return html_path

    def execute_weekly(self, target_date: str = "") -> str:
        """执行周报生成"""
        logger.info("═══ 呈现总指挥启动（周报）═══")
        html_path = self.weekly_builder.build(target_date)
        if html_path:
            self._update_index()
        logger.info("═══ 呈现总指挥完成（周报）═══: %s", html_path)
        return html_path

    def execute_monthly(self, target_date: str = "") -> str:
        """执行月报生成"""
        logger.info("═══ 呈现总指挥启动（月报）═══")
        html_path = self.monthly_builder.build(target_date)
        if html_path:
            self._update_index()
        logger.info("═══ 呈现总指挥完成（月报）═══: %s", html_path)
        return html_path

    def _update_index(self):
        """更新归档索引页"""
        daily_reports = self.db.get_all_daily_reports()
        weekly_reports = self.db.get_all_weekly_reports()
        monthly_reports = self.db.get_all_monthly_reports()

        # 日报列表（含精选链接）
        daily_html = ""
        for r in daily_reports:
            elite_link = r.html_path.replace("daily/", "elite/")
            daily_html += (
                f'<tr><td>{r.report_date}</td>'
                f'<td>{r.article_count}篇</td>'
                f'<td><a href="{r.html_path}">全量简报</a> | '
                f'<a href="{elite_link}" style="color:#B8860B;font-weight:bold">精选报送</a></td></tr>\n'
            )

        # 周报列表
        weekly_html = ""
        for r in weekly_reports:
            weekly_html += (
                f'<tr><td>{r.year}年第{r.week_number}周</td>'
                f'<td>{r.week_start} ~ {r.week_end}</td>'
                f'<td>{r.article_count}篇</td>'
                f'<td><a href="{r.html_path}">查看</a></td></tr>\n'
            )

        # 月报列表
        monthly_html = ""
        for r in monthly_reports:
            monthly_html += (
                f'<tr><td>{r.year}年{r.month}月</td>'
                f'<td>{r.article_count}篇</td>'
                f'<td><a href="{r.html_path}">查看</a></td></tr>\n'
            )

        index_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{REPORT_TITLE} - 简报归档</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            background: #f5f5f5; color: #333; line-height: 1.8;
        }}
        .container {{
            max-width: 800px; margin: 20px auto; background: #fff;
            padding: 40px 50px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .header-line {{ border-top: 3px solid #8B0000; margin-bottom: 30px; }}
        h1 {{
            text-align: center; color: #8B0000; font-size: 26px;
            letter-spacing: 3px; margin-bottom: 5px;
        }}
        .subtitle {{
            text-align: center; color: #666; font-size: 13px;
            margin-bottom: 25px; letter-spacing: 2px;
        }}
        h2 {{
            color: #8B0000; font-size: 18px; margin: 25px 0 10px;
            border-bottom: 1px solid #ddd; padding-bottom: 5px;
        }}
        table {{
            width: 100%; border-collapse: collapse; margin: 10px 0 20px;
        }}
        th, td {{
            padding: 8px 12px; text-align: left; font-size: 14px;
            border-bottom: 1px solid #eee;
        }}
        th {{ background: #f8f8f8; color: #555; font-weight: normal; }}
        a {{ color: #003366; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .empty {{ color: #999; font-size: 14px; padding: 10px 0; }}
        @media (max-width: 600px) {{
            .container {{ padding: 20px 15px; margin: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-line"></div>
        <h1>{REPORT_TITLE}</h1>
        <p class="subtitle">AI INTELLIGENCE BRIEF ARCHIVE</p>

        <h2>📋 每日简报</h2>
        {"<table><tr><th>日期</th><th>文章数</th><th>操作</th></tr>" + daily_html + "</table>" if daily_html else '<p class="empty">暂无日报</p>'}

        <h2>📊 每周汇总</h2>
        {"<table><tr><th>周次</th><th>日期范围</th><th>文章数</th><th>操作</th></tr>" + weekly_html + "</table>" if weekly_html else '<p class="empty">暂无周报</p>'}

        <h2>📈 每月汇总</h2>
        {"<table><tr><th>月份</th><th>文章数</th><th>操作</th></tr>" + monthly_html + "</table>" if monthly_html else '<p class="empty">暂无月报</p>'}
    </div>
</body>
</html>"""

        index_path = DOCS_DIR / "index.html"
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        index_path.write_text(index_html, encoding="utf-8")
        logger.info("索引页已更新: %s", index_path)
