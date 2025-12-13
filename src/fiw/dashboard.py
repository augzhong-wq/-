from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from flask import Flask, render_template, request

from fiw.config import Settings


def _load_day(settings: Settings, day: str, view: str) -> pd.DataFrame:
    p = settings.daily_dir / day / ("full.csv" if view == "full" else "brief.csv")
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def create_app(settings: Settings) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent / "templates"),
        static_folder=None,
    )

    @app.get("/")
    def index():
        view = request.args.get("view", "brief")
        day = request.args.get("day", date.today().isoformat())
        cat = request.args.get("cat", "")
        lvl = request.args.get("lvl", "")
        q = request.args.get("q", "")

        df = _load_day(settings, day=day, view=view)
        if not df.empty:
            if cat:
                df = df[df["category"] == cat]
            if lvl:
                df = df[df["importance_level"] == lvl]
            if q:
                qq = q.lower()
                df = df[df["title"].astype(str).str.lower().str.contains(qq) | df["summary"].astype(str).str.lower().str.contains(qq)]

        cats = sorted([c for c in df["category"].unique().tolist() if c]) if not df.empty and "category" in df.columns else []
        lvls = ["S", "A", "B", "C"]

        return render_template(
            "index.html",
            day=day,
            view=view,
            cat=cat,
            lvl=lvl,
            q=q,
            cats=cats,
            lvls=lvls,
            rows=(df.to_dict(orient="records") if not df.empty else []),
            total=(len(df) if not df.empty else 0),
        )

    return app


def run_server(settings: Settings, host: str = "0.0.0.0", port: int = 8080) -> None:
    app = create_app(settings)
    app.run(host=host, port=port, debug=False)
