from __future__ import annotations

import argparse
from datetime import date

from dotenv import load_dotenv

from fiw.config import load_settings
from fiw.collector import collect_for_date
from fiw.dashboard import run_server
from fiw.weekly import build_daily_views, build_weekly_package
from fiw.push import push_weekly_package


def _parse_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def collect() -> None:
    load_dotenv()
    settings = load_settings()

    p = argparse.ArgumentParser()
    p.add_argument("--date", default=str(date.today()))
    p.add_argument("--max-items", type=int, default=800)
    args = p.parse_args()

    dt = _parse_date(args.date)
    collect_for_date(settings=settings, day=dt, max_items=args.max_items)


def build_daily() -> None:
    load_dotenv()
    settings = load_settings()

    p = argparse.ArgumentParser()
    p.add_argument("--date", default=str(date.today()))
    args = p.parse_args()
    dt = _parse_date(args.date)

    build_daily_views(settings=settings, day=dt)


def build_weekly() -> None:
    load_dotenv()
    settings = load_settings()

    p = argparse.ArgumentParser()
    p.add_argument("--week-start", help="YYYY-MM-DD (Monday)", default=None)
    args = p.parse_args()

    build_weekly_package(settings=settings, week_start=args.week_start)


def serve() -> None:
    load_dotenv()
    settings = load_settings()

    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8080)
    args = p.parse_args()

    run_server(settings=settings, host=args.host, port=args.port)


def push_weekly() -> None:
    load_dotenv()
    settings = load_settings()

    p = argparse.ArgumentParser()
    p.add_argument("--week-start", help="YYYY-MM-DD (Monday)", default=None)
    args = p.parse_args()

    pkg = build_weekly_package(settings=settings, week_start=args.week_start)
    push_weekly_package(settings=settings, weekly_package=pkg)
