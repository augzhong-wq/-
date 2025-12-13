from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


def _register_fonts() -> None:
    # 使用内置 CID 字体（支持中文）。若需要更接近样例字体，可改为加载本地TTF。
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    except Exception:
        pass


def _draw_header(c: canvas.Canvas, title: str, week_id: str, pub_date: date) -> None:
    w, h = A4
    # 顶部机构标识（文本占位，支持后续替换为图片）
    c.setFont("STSong-Light", 12)
    c.setFillColor(colors.red)
    c.drawString(20 * mm, h - 18 * mm, "CCID")
    c.setFillColor(colors.black)
    c.setFont("STSong-Light", 10)
    c.drawString(32 * mm, h - 18 * mm, "未来产业研究中心")

    # 大标题
    c.setFont("STSong-Light", 36)
    c.setFillColor(colors.red)
    c.drawCentredString(w / 2, h - 55 * mm, title)

    # 期号 + 日期
    c.setFillColor(colors.black)
    c.setFont("STSong-Light", 12)
    c.drawString(20 * mm, h - 75 * mm, f"{week_id} 期")
    c.drawRightString(w - 20 * mm, h - 75 * mm, f"{pub_date.year} 年 {pub_date.month} 月 {pub_date.day} 日")

    # 红线
    c.setStrokeColor(colors.red)
    c.setLineWidth(1.5)
    c.line(20 * mm, h - 78 * mm, w - 20 * mm, h - 78 * mm)


def _draw_keywords(c: canvas.Canvas, keywords: list[str], y: float) -> float:
    c.setFont("STSong-Light", 12)
    c.setFillColor(colors.black)
    c.drawString(20 * mm, y, "关键词：" + "、".join(keywords))
    return y - 12 * mm


def _draw_section_title(c: canvas.Canvas, text: str, y: float) -> float:
    c.setFont("STSong-Light", 14)
    c.drawString(20 * mm, y, f"➤ {text}")
    return y - 10 * mm


def _wrap_text(c: canvas.Canvas, text: str, max_width: float, font_name: str, font_size: int) -> list[str]:
    # 简单按字符宽度估算换行（中英文混排可用；若要更精细可改为platypus）
    c.setFont(font_name, font_size)
    out = []
    cur = ""
    for ch in text:
        if ch == "\n":
            out.append(cur)
            cur = ""
            continue
        nxt = cur + ch
        if c.stringWidth(nxt, font_name, font_size) <= max_width:
            cur = nxt
        else:
            if cur:
                out.append(cur)
            cur = ch
    if cur:
        out.append(cur)
    return out


def _draw_item(c: canvas.Canvas, idx: int, title: str, body: str | None, source: str | None, y: float) -> float:
    w, h = A4
    left = 20 * mm
    right = w - 20 * mm

    # 标题（加粗效果用更大字号近似）
    c.setFont("STSong-Light", 13)
    c.setFillColor(colors.black)
    head = f"{idx}、{title.strip()}"
    lines = _wrap_text(c, head, right - left, "STSong-Light", 13)
    for ln in lines:
        c.drawString(left, y, ln)
        y -= 7 * mm

    # 正文
    if body:
        c.setFont("STSong-Light", 12)
        body_lines = _wrap_text(c, body.strip(), right - left - 6 * mm, "STSong-Light", 12)
        for ln in body_lines[:10]:
            c.drawString(left + 6 * mm, y, ln)
            y -= 6 * mm

    # 来源（蓝色括号）
    if source:
        c.setFont("STSong-Light", 11)
        c.setFillColor(colors.blue)
        c.drawString(left + 6 * mm, y, f"（新闻来源：{source}）")
        c.setFillColor(colors.black)
        y -= 8 * mm

    return y - 2 * mm


def render_weekly_pdf(pdf_path: Path, week_id: str, monday: date, keywords: list[str], df_top: pd.DataFrame) -> None:
    _register_fonts()

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    w, h = A4

    pub_date = monday  # 样例为周一日期

    # ---- Page 1 ----
    _draw_header(c, "未来产业周度要闻", week_id, pub_date)
    y = h - 92 * mm
    y = _draw_keywords(c, keywords, y)

    # 栏目拆解：本周头条/动态/简讯
    # 这里先按重要性分层，后续可按更细分类映射到样例栏目。
    df = df_top.copy()
    if not df.empty and "importance_level" in df.columns:
        df["_lvl"] = df["importance_level"].astype(str)
    else:
        df["_lvl"] = "B"

    # 本周头条：S/A
    y = _draw_section_title(c, "本周头条", y)
    heads = df[df["_lvl"].isin(["S", "A"])].head(5)
    idx = 1
    for _, r in heads.iterrows():
        title = str(r.get("title", ""))
        body = str(r.get("summary", "") or "").strip()
        source = str(r.get("source_name", ""))
        y = _draw_item(c, idx, title, body, source, y)
        idx += 1
        if y < 25 * mm:
            break

    c.setFont("STSong-Light", 10)
    c.drawCentredString(w / 2, 12 * mm, "1")
    c.showPage()

    # ---- Page 2+ ----
    page_no = 2
    remaining = df[~df.index.isin(heads.index)]
    # 动态：A/B
    blocks = [
        ("动态", remaining[remaining["_lvl"].isin(["A", "B"])].head(20)),
        ("简讯", remaining[remaining["_lvl"].isin(["B", "C"])].head(30)),
    ]

    for section_name, section_df in blocks:
        if section_df.empty:
            continue
        # 每个section可能跨多页
        i = 1
        y = h - 20 * mm
        c.setFont("STSong-Light", 12)
        c.setFillColor(colors.black)
        c.drawString(20 * mm, y, "CCID 未来产业研究中心")
        y -= 10 * mm
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.5)
        c.line(20 * mm, y, w - 20 * mm, y)
        y -= 12 * mm

        y = _draw_section_title(c, section_name, y)

        for _, r in section_df.iterrows():
            title = str(r.get("title", ""))
            body = str(r.get("summary", "") or "").strip()
            source = str(r.get("source_name", ""))
            y = _draw_item(c, i, title, body, source, y)
            i += 1
            if y < 25 * mm:
                c.setFont("STSong-Light", 10)
                c.drawCentredString(w / 2, 12 * mm, str(page_no))
                c.showPage()
                page_no += 1

                y = h - 20 * mm
                c.setFont("STSong-Light", 12)
                c.drawString(20 * mm, y, "CCID 未来产业研究中心")
                y -= 10 * mm
                c.setStrokeColor(colors.lightgrey)
                c.line(20 * mm, y, w - 20 * mm, y)
                y -= 12 * mm
                y = _draw_section_title(c, section_name, y)

        c.setFont("STSong-Light", 10)
        c.drawCentredString(w / 2, 12 * mm, str(page_no))
        c.showPage()
        page_no += 1

    c.save()
