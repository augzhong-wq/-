"""数据模型定义"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawArticle:
    """原始采集文章"""
    source_name: str                        # 信息源名称
    source_category: str                    # 信息源大类
    source_sub_category: str                # 信息源子类
    url: str                                # 文章URL
    title: str                              # 标题
    content_snippet: str = ""               # 内容摘要（前500字）
    published_date: Optional[str] = None    # 发布日期
    collected_at: str = ""                  # 采集时间
    content_hash: str = ""                  # 内容哈希（用于去重）
    id: Optional[int] = None               # 数据库ID

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.utcnow().isoformat()


@dataclass
class CuratedArticle:
    """筛选后的文章"""
    raw_article_id: int                     # 关联原始文章ID
    title_zh: str                           # 中文标题
    summary_zh: str                         # 中文精编摘要
    category: str                           # 分类（技术突破/政策监管等）
    importance_score: int = 3               # 重要性评分 1-5
    is_selected_for_report: bool = False    # 是否入选简报
    source_name: str = ""                   # 来源名称
    source_url: str = ""                    # 原文链接
    published_date: Optional[str] = None    # 发布日期
    curated_at: str = ""                    # 筛选时间
    report_date: str = ""                   # 报送日期
    id: Optional[int] = None               # 数据库ID

    def __post_init__(self):
        if not self.curated_at:
            self.curated_at = datetime.utcnow().isoformat()

    @property
    def importance_stars(self) -> str:
        """返回星级标记"""
        return "★" * self.importance_score


@dataclass
class DailyReport:
    """每日简报"""
    report_date: str                        # 报告日期 YYYY-MM-DD
    html_path: str                          # HTML文件路径
    article_count: int = 0                  # 文章数量
    source_count: int = 0                   # 信息源数量
    total_collected: int = 0                # 总采集数
    generated_at: str = ""                  # 生成时间
    id: Optional[int] = None

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat()


@dataclass
class WeeklyReport:
    """每周汇总"""
    week_start: str                         # 周起始日期
    week_end: str                           # 周结束日期
    year: int = 0                           # 年份
    week_number: int = 0                    # 周数
    html_path: str = ""                     # HTML文件路径
    article_count: int = 0
    generated_at: str = ""
    id: Optional[int] = None

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat()


@dataclass
class MonthlyReport:
    """每月汇总"""
    year: int                               # 年份
    month: int                              # 月份
    html_path: str = ""                     # HTML文件路径
    article_count: int = 0
    generated_at: str = ""
    id: Optional[int] = None

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat()
