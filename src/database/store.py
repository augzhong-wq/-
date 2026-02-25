"""数据库操作层 - SQLite"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from src.database.models import (
    RawArticle, CuratedArticle, DailyReport, WeeklyReport, MonthlyReport
)
from src.config.settings import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseStore:
    """SQLite数据库操作封装"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS raw_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    source_category TEXT NOT NULL,
                    source_sub_category TEXT DEFAULT '',
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content_snippet TEXT DEFAULT '',
                    published_date TEXT,
                    collected_at TEXT NOT NULL,
                    content_hash TEXT DEFAULT '',
                    UNIQUE(url, collected_at)
                );

                CREATE TABLE IF NOT EXISTS curated_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_article_id INTEGER,
                    title_zh TEXT NOT NULL,
                    summary_zh TEXT DEFAULT '',
                    category TEXT NOT NULL,
                    importance_score INTEGER DEFAULT 3,
                    is_selected_for_report INTEGER DEFAULT 0,
                    source_name TEXT DEFAULT '',
                    source_url TEXT DEFAULT '',
                    published_date TEXT,
                    curated_at TEXT NOT NULL,
                    report_date TEXT NOT NULL,
                    FOREIGN KEY (raw_article_id) REFERENCES raw_articles(id)
                );

                CREATE TABLE IF NOT EXISTS daily_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_date TEXT NOT NULL UNIQUE,
                    html_path TEXT NOT NULL,
                    article_count INTEGER DEFAULT 0,
                    source_count INTEGER DEFAULT 0,
                    total_collected INTEGER DEFAULT 0,
                    generated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS weekly_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_start TEXT NOT NULL,
                    week_end TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    week_number INTEGER NOT NULL,
                    html_path TEXT DEFAULT '',
                    article_count INTEGER DEFAULT 0,
                    generated_at TEXT NOT NULL,
                    UNIQUE(year, week_number)
                );

                CREATE TABLE IF NOT EXISTS monthly_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    html_path TEXT DEFAULT '',
                    article_count INTEGER DEFAULT 0,
                    generated_at TEXT NOT NULL,
                    UNIQUE(year, month)
                );

                CREATE INDEX IF NOT EXISTS idx_raw_url ON raw_articles(url);
                CREATE INDEX IF NOT EXISTS idx_raw_hash ON raw_articles(content_hash);
                CREATE INDEX IF NOT EXISTS idx_raw_collected ON raw_articles(collected_at);
                CREATE INDEX IF NOT EXISTS idx_curated_date ON curated_articles(report_date);
                CREATE INDEX IF NOT EXISTS idx_curated_score ON curated_articles(importance_score);
                CREATE INDEX IF NOT EXISTS idx_curated_selected ON curated_articles(is_selected_for_report);
            """)
            conn.commit()
            logger.info("数据库初始化完成: %s", self.db_path)
        finally:
            conn.close()

    # ─── Raw Articles ────────────────────────────────────

    def insert_raw_article(self, article: RawArticle) -> int:
        """插入原始文章，返回ID"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO raw_articles
                   (source_name, source_category, source_sub_category, url, title,
                    content_snippet, published_date, collected_at, content_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (article.source_name, article.source_category,
                 article.source_sub_category, article.url, article.title,
                 article.content_snippet, article.published_date,
                 article.collected_at, article.content_hash)
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def insert_raw_articles_batch(self, articles: list[RawArticle]) -> int:
        """批量插入原始文章，返回插入数量"""
        conn = self._get_conn()
        count = 0
        try:
            for article in articles:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO raw_articles
                           (source_name, source_category, source_sub_category, url, title,
                            content_snippet, published_date, collected_at, content_hash)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (article.source_name, article.source_category,
                         article.source_sub_category, article.url, article.title,
                         article.content_snippet, article.published_date,
                         article.collected_at, article.content_hash)
                    )
                    count += 1
                except sqlite3.IntegrityError:
                    pass
            conn.commit()
            return count
        finally:
            conn.close()

    def url_exists(self, url: str) -> bool:
        """检查URL是否已存在"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM raw_articles WHERE url = ? LIMIT 1", (url,)
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def get_raw_articles_today(self) -> list[RawArticle]:
        """获取今天采集的所有原始文章"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT * FROM raw_articles
                   WHERE collected_at LIKE ?
                   ORDER BY source_name""",
                (f"{today}%",)
            ).fetchall()
            return [self._row_to_raw_article(r) for r in rows]
        finally:
            conn.close()

    # ─── Curated Articles ────────────────────────────────

    def insert_curated_article(self, article: CuratedArticle) -> int:
        """插入筛选后的文章"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO curated_articles
                   (raw_article_id, title_zh, summary_zh, category,
                    importance_score, is_selected_for_report, source_name,
                    source_url, published_date, curated_at, report_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (article.raw_article_id, article.title_zh, article.summary_zh,
                 article.category, article.importance_score,
                 int(article.is_selected_for_report), article.source_name,
                 article.source_url, article.published_date,
                 article.curated_at, article.report_date)
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def insert_curated_articles_batch(self, articles: list[CuratedArticle]) -> int:
        """批量插入筛选后的文章"""
        conn = self._get_conn()
        count = 0
        try:
            for article in articles:
                conn.execute(
                    """INSERT INTO curated_articles
                       (raw_article_id, title_zh, summary_zh, category,
                        importance_score, is_selected_for_report, source_name,
                        source_url, published_date, curated_at, report_date)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (article.raw_article_id, article.title_zh, article.summary_zh,
                     article.category, article.importance_score,
                     int(article.is_selected_for_report), article.source_name,
                     article.source_url, article.published_date,
                     article.curated_at, article.report_date)
                )
                count += 1
            conn.commit()
            return count
        finally:
            conn.close()

    def get_curated_articles_for_report(self, report_date: str) -> list[CuratedArticle]:
        """获取某日入选简报的文章"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT * FROM curated_articles
                   WHERE report_date = ? AND is_selected_for_report = 1
                   ORDER BY importance_score DESC, category""",
                (report_date,)
            ).fetchall()
            return [self._row_to_curated_article(r) for r in rows]
        finally:
            conn.close()

    def get_curated_articles_by_date_range(
        self, start_date: str, end_date: str
    ) -> list[CuratedArticle]:
        """获取日期范围内的筛选文章"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT * FROM curated_articles
                   WHERE report_date >= ? AND report_date <= ?
                     AND is_selected_for_report = 1
                   ORDER BY importance_score DESC, category""",
                (start_date, end_date)
            ).fetchall()
            return [self._row_to_curated_article(r) for r in rows]
        finally:
            conn.close()

    # ─── Reports ─────────────────────────────────────────

    def insert_daily_report(self, report: DailyReport) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT OR REPLACE INTO daily_reports
                   (report_date, html_path, article_count, source_count,
                    total_collected, generated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (report.report_date, report.html_path, report.article_count,
                 report.source_count, report.total_collected, report.generated_at)
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def insert_weekly_report(self, report: WeeklyReport) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT OR REPLACE INTO weekly_reports
                   (week_start, week_end, year, week_number, html_path,
                    article_count, generated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (report.week_start, report.week_end, report.year,
                 report.week_number, report.html_path, report.article_count,
                 report.generated_at)
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def insert_monthly_report(self, report: MonthlyReport) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT OR REPLACE INTO monthly_reports
                   (year, month, html_path, article_count, generated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (report.year, report.month, report.html_path,
                 report.article_count, report.generated_at)
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def get_all_daily_reports(self) -> list[DailyReport]:
        """获取所有日报记录"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM daily_reports ORDER BY report_date DESC"
            ).fetchall()
            return [DailyReport(
                report_date=r["report_date"], html_path=r["html_path"],
                article_count=r["article_count"], source_count=r["source_count"],
                total_collected=r["total_collected"], generated_at=r["generated_at"],
                id=r["id"]
            ) for r in rows]
        finally:
            conn.close()

    def get_all_weekly_reports(self) -> list[WeeklyReport]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM weekly_reports ORDER BY year DESC, week_number DESC"
            ).fetchall()
            return [WeeklyReport(
                week_start=r["week_start"], week_end=r["week_end"],
                year=r["year"], week_number=r["week_number"],
                html_path=r["html_path"], article_count=r["article_count"],
                generated_at=r["generated_at"], id=r["id"]
            ) for r in rows]
        finally:
            conn.close()

    def get_all_monthly_reports(self) -> list[MonthlyReport]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM monthly_reports ORDER BY year DESC, month DESC"
            ).fetchall()
            return [MonthlyReport(
                year=r["year"], month=r["month"],
                html_path=r["html_path"], article_count=r["article_count"],
                generated_at=r["generated_at"], id=r["id"]
            ) for r in rows]
        finally:
            conn.close()

    # ─── Maintenance ─────────────────────────────────────

    def cleanup_old_raw_articles(self, days: int = 90):
        """清理超过指定天数的原始文章"""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        conn = self._get_conn()
        try:
            result = conn.execute(
                "DELETE FROM raw_articles WHERE collected_at < ?", (cutoff,)
            )
            conn.commit()
            logger.info("清理了 %d 条过期原始文章（%d天前）", result.rowcount, days)
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """获取数据库统计信息"""
        conn = self._get_conn()
        try:
            raw_count = conn.execute("SELECT COUNT(*) FROM raw_articles").fetchone()[0]
            curated_count = conn.execute("SELECT COUNT(*) FROM curated_articles").fetchone()[0]
            daily_count = conn.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0]
            weekly_count = conn.execute("SELECT COUNT(*) FROM weekly_reports").fetchone()[0]
            monthly_count = conn.execute("SELECT COUNT(*) FROM monthly_reports").fetchone()[0]
            return {
                "raw_articles": raw_count,
                "curated_articles": curated_count,
                "daily_reports": daily_count,
                "weekly_reports": weekly_count,
                "monthly_reports": monthly_count,
            }
        finally:
            conn.close()

    # ─── Private Helpers ─────────────────────────────────

    @staticmethod
    def _row_to_raw_article(row: sqlite3.Row) -> RawArticle:
        return RawArticle(
            id=row["id"],
            source_name=row["source_name"],
            source_category=row["source_category"],
            source_sub_category=row["source_sub_category"],
            url=row["url"],
            title=row["title"],
            content_snippet=row["content_snippet"],
            published_date=row["published_date"],
            collected_at=row["collected_at"],
            content_hash=row["content_hash"],
        )

    @staticmethod
    def _row_to_curated_article(row: sqlite3.Row) -> CuratedArticle:
        return CuratedArticle(
            id=row["id"],
            raw_article_id=row["raw_article_id"],
            title_zh=row["title_zh"],
            summary_zh=row["summary_zh"],
            category=row["category"],
            importance_score=row["importance_score"],
            is_selected_for_report=bool(row["is_selected_for_report"]),
            source_name=row["source_name"],
            source_url=row["source_url"],
            published_date=row["published_date"],
            curated_at=row["curated_at"],
            report_date=row["report_date"],
        )
