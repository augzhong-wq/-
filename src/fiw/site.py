from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from fiw.config import Settings


@dataclass
class SiteBuildResult:
    out_dir: Path
    index_path: Path


def _jinja_env(settings: Settings) -> Environment:
    tpl_dir = Path(__file__).resolve().parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals["build_time"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    return env


def _list_days(daily_dir: Path) -> list[str]:
    if not daily_dir.exists():
        return []
    days = [p.name for p in daily_dir.iterdir() if p.is_dir()]
    # YYYY-MM-DD 字符串排序即可
    return sorted(days, reverse=True)


def _load_daily_csv(settings: Settings, day: str, view: str) -> pd.DataFrame:
    p = settings.daily_dir / day / ("full.csv" if view == "full" else "brief.csv")
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def build_static_site(settings: Settings, out_dir: Path | None = None, max_days: int = 60) -> SiteBuildResult:
    """
    生成 GitHub Pages 可发布的静态站点。
    - /index.html：最近若干天列表 + 默认显示最新一天（精简版）
    - /days/<YYYY-MM-DD>/(brief|full).html：当日表格页面
    """
    out = (out_dir or (settings.project_root / "site")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "days").mkdir(parents=True, exist_ok=True)

    env = _jinja_env(settings)
    tpl_index = env.get_template("site_index.html")
    tpl_day = env.get_template("site_day.html")

    days = _list_days(settings.daily_dir)[:max_days]
    latest = days[0] if days else date.today().isoformat()

    # 生成每一天两种视图
    for d in days:
        for view in ("brief", "full"):
            df = _load_daily_csv(settings, d, view=view)
            rows = df.to_dict(orient="records") if not df.empty else []
            cats = sorted({r.get("category") for r in rows if r.get("category")})
            day_dir = out / "days" / d
            day_dir.mkdir(parents=True, exist_ok=True)
            html = tpl_day.render(day=d, view=view, rows=rows, cats=cats, total=len(rows))
            (day_dir / f"{view}.html").write_text(html, encoding="utf-8")

    # index：链接到最新一天
    html_index = tpl_index.render(days=days, latest=latest)
    index_path = out / "index.html"
    index_path.write_text(html_index, encoding="utf-8")

    return SiteBuildResult(out_dir=out, index_path=index_path)

