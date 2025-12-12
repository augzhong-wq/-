from __future__ import annotations

import json
import time
from dataclasses import dataclass

import requests

from fiw.config import Settings


@dataclass
class LLMResult:
    category: str | None
    importance_score: float | None
    importance_level: str | None
    importance_reason: str | None
    summary_zh: str | None
    extra: dict


SYSTEM_PROMPT_ZH = """你是“未来产业周度要闻”的研判助手。
目标：对给定新闻（标题/摘要/来源/链接）做：中文摘要、栏目归类、重要性评分、重要性原因。

栏目（category）只能选一个：
政策、企业、学术、投融资、安全、其他

importance_score：0~10 的浮点数（越高越重要）
importance_level：S/A/B/C（S>=8.2, A>=6.6, B>=4.6, else C）

优先识别并加权的重要事件（包括但不限于）：
- 重大政策/行政令/法案/监管规则、出口管制/制裁/反制、实体清单/黑名单、关税、CFIUS/OFAC相关动作
- AI/芯片/算力/机器人等重大产品发布、重大合作、量产/部署
- 重大投融资/并购/IPO/巨额订单
- 国家级战略/国际协定/联盟

输出必须是严格 JSON（不要 markdown），字段：
{
  "category": "...",
  "importance_score": 0-10,
  "importance_level": "S|A|B|C",
  "importance_reason": "一句话，说明为什么重要",
  "summary_zh": "2-3句中文摘要",
  "signals": ["可选：命中要素，如‘行政令’‘出口管制’‘并购’等"]
}
"""


def _post_chat(settings: Settings, messages: list[dict], timeout: int = 40) -> dict:
    url = settings.deepseek_base_url.rstrip("/") + "/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.deepseek_model,
        "messages": messages,
        "temperature": 0.2,
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
    r.raise_for_status()
    return r.json()


def analyze_item(settings: Settings, title: str, summary: str | None, source_name: str, url: str) -> LLMResult:
    if not settings.deepseek_api_key:
        return LLMResult(None, None, None, None, None, extra={})

    user = {
        "role": "user",
        "content": json.dumps(
            {
                "title": title,
                "summary": summary,
                "source_name": source_name,
                "url": url,
            },
            ensure_ascii=False,
        ),
    }
    msgs = [{"role": "system", "content": SYSTEM_PROMPT_ZH}, user]

    # 简单重试
    last_err: str | None = None
    for i in range(3):
        try:
            data = _post_chat(settings, msgs, timeout=45)
            content = data["choices"][0]["message"]["content"]
            obj = json.loads(content)
            return LLMResult(
                category=obj.get("category"),
                importance_score=float(obj["importance_score"]) if obj.get("importance_score") is not None else None,
                importance_level=obj.get("importance_level"),
                importance_reason=obj.get("importance_reason"),
                summary_zh=obj.get("summary_zh"),
                extra={"signals": obj.get("signals"), "raw": obj},
            )
        except Exception as e:
            last_err = str(e)
            time.sleep(0.6 * (i + 1))

    return LLMResult(None, None, None, None, None, extra={"error": last_err})

