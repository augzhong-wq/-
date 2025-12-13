from __future__ import annotations

import mimetypes
import smtplib
from email.message import EmailMessage

import requests

from fiw.config import Settings
from fiw.weekly import WeeklyPackage


def _send_email(settings: Settings, subject: str, body: str, attachment_path: str | None = None) -> None:
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_pass and settings.smtp_from and settings.smtp_to):
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = settings.smtp_to
    msg.set_content(body)

    if attachment_path:
        ctype, _ = mimetypes.guess_type(attachment_path)
        maintype, subtype = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
        with open(attachment_path, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=attachment_path.split("/")[-1])

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as s:
        s.starttls()
        s.login(settings.smtp_user, settings.smtp_pass)
        s.send_message(msg)


def _send_wecom(settings: Settings, text: str) -> None:
    if not settings.wecom_webhook:
        return
    requests.post(settings.wecom_webhook, json={"msgtype": "text", "text": {"content": text}}, timeout=20).raise_for_status()


def push_weekly_package(settings: Settings, weekly_package: WeeklyPackage) -> None:
    subj = f"未来产业周度要闻 {weekly_package.week_id}"
    body = f"周报已生成：{weekly_package.pdf_path}\n\n包含：\n- 周内全量CSV：{weekly_package.raw_merged_csv}\n- Top条目CSV：{weekly_package.top_csv}\n"

    # 邮件（附PDF）
    _send_email(settings, subject=subj, body=body, attachment_path=str(weekly_package.pdf_path))

    # 企业微信（只发文本；如需发文件/图床链接可在此扩展）
    _send_wecom(settings, text=body)
