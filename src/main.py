"""
AI每日动态监测与简报生成系统 - 主入口

用法：
    python -m src.main --mode daily          # 每日采集+简报
    python -m src.main --mode weekly         # 每周汇总
    python -m src.main --mode monthly        # 每月汇总
    python -m src.main --mode daily --test   # 测试模式（仅采集3个源）
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime, timezone, timedelta

from src.config.settings import LOG_LEVEL, LOG_FORMAT
from src.database.store import DatabaseStore
from src.llm.client import LLMClient


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_beijing_date() -> str:
    """获取北京时间日期"""
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz).strftime("%Y-%m-%d")


async def run_daily(test_mode: bool = False):
    """执行每日采集+简报流程"""
    logger = logging.getLogger("main")
    start_time = time.time()
    report_date = get_beijing_date()

    logger.info("=" * 60)
    logger.info("  AI每日动态监测系统 - 每日采集")
    logger.info("  报送日期: %s", report_date)
    logger.info("  测试模式: %s", "是" if test_mode else "否")
    logger.info("=" * 60)

    # 初始化组件
    db = DatabaseStore()
    llm = LLMClient()

    # ─── Agent 1: 采集总指挥 ──────────────────────────
    logger.info("\n▶ Agent 1: 采集总指挥启动...")
    from src.collectors.commander import CollectionCommander
    collection_commander = CollectionCommander()
    raw_articles = await collection_commander.execute(test_mode=test_mode)
    collection_stats = collection_commander.get_stats()
    logger.info("▶ Agent 1 完成: 采集 %d 篇文章", len(raw_articles))

    if not raw_articles:
        logger.warning("未采集到任何文章，流程终止")
        return

    # ─── Agent 2: 筛选总指挥 ──────────────────────────
    logger.info("\n▶ Agent 2: 筛选总指挥启动...")
    from src.curators.commander import CurationCommander
    curation_commander = CurationCommander(db, llm)
    selected_articles = curation_commander.execute(raw_articles, report_date)
    curation_stats = curation_commander.get_stats()
    logger.info("▶ Agent 2 完成: 入选 %d 篇", len(selected_articles))

    if not selected_articles:
        logger.warning("无文章入选简报")
        # 仍然生成空报告
        selected_articles = []

    # ─── Agent 3: 呈现总指挥 ──────────────────────────
    logger.info("\n▶ Agent 3: 呈现总指挥启动...")
    from src.presenters.commander import PresentationCommander
    presentation_commander = PresentationCommander(db, llm)
    html_path = presentation_commander.execute_daily(
        articles=selected_articles,
        report_date=report_date,
        collection_stats=collection_stats,
        curation_stats=curation_stats,
    )
    logger.info("▶ Agent 3 完成: %s", html_path)

    # 导出每日CSV数据
    logger.info("\n▶ 导出每日CSV数据...")
    db.export_daily_csv(report_date)

    # 清理过期数据
    db.cleanup_old_raw_articles(days=90)

    elapsed = time.time() - start_time
    logger.info("\n" + "=" * 60)
    logger.info("  每日流程完成")
    logger.info("  采集: %d 篇 → 入选: %d 篇",
                len(raw_articles), len(selected_articles))
    logger.info("  输出: %s", html_path)
    logger.info("  总耗时: %.1f秒 (%.1f分钟)", elapsed, elapsed / 60)
    logger.info("=" * 60)


async def run_weekly():
    """执行每周汇总"""
    logger = logging.getLogger("main")
    logger.info("=" * 60)
    logger.info("  AI每日动态监测系统 - 每周汇总")
    logger.info("=" * 60)

    db = DatabaseStore()
    llm = LLMClient()

    from src.presenters.commander import PresentationCommander
    commander = PresentationCommander(db, llm)
    html_path = commander.execute_weekly()

    if html_path:
        logger.info("周报已生成: %s", html_path)
    else:
        logger.warning("周报生成失败或无数据")


async def run_monthly():
    """执行每月汇总"""
    logger = logging.getLogger("main")
    logger.info("=" * 60)
    logger.info("  AI每日动态监测系统 - 每月汇总")
    logger.info("=" * 60)

    db = DatabaseStore()
    llm = LLMClient()

    from src.presenters.commander import PresentationCommander
    commander = PresentationCommander(db, llm)
    html_path = commander.execute_monthly()

    if html_path:
        logger.info("月报已生成: %s", html_path)
    else:
        logger.warning("月报生成失败或无数据")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AI每日动态监测与简报生成系统"
    )
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="运行模式: daily=每日采集, weekly=每周汇总, monthly=每月汇总"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="测试模式（仅采集前3个源）"
    )
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("main")

    try:
        if args.mode == "daily":
            asyncio.run(run_daily(test_mode=args.test))
        elif args.mode == "weekly":
            asyncio.run(run_weekly())
        elif args.mode == "monthly":
            asyncio.run(run_monthly())
    except KeyboardInterrupt:
        logger.info("用户中断执行")
        sys.exit(1)
    except Exception as e:
        logger.error("执行失败: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
