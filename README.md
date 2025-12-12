## Future-Industry-Weekly-Post

一个“未来产业周度要闻”的自动采集、重要性分析、可视化看板与周报PDF生成系统。

### 你将得到什么

- **每天 08:00 自动采集**：国内外科技企业 / 学术机构 / 国家政策 / 投融资等动态（RSS + GDELT 全网检索为主）
- **采集结果全部落地 CSV**：可追溯、可审计、可二次分析
- **每日 HTML 看板**：分“精简版 / 完整版”，支持筛选与搜索
- **每周一 08:00 自动生成周报 PDF**：版式与栏目对标你提供的样例（第一版已实现，后续可继续逼近字体/间距/栏目映射）

### 快速开始

```bash
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
cp .env.example .env

# 采集当天
python3 -m fiw collect --date 2025-12-12
# 构建当天精简/全量视图
python3 -m fiw build-daily --date 2025-12-12

# 启动看板
python3 -m fiw serve --port 8080

# 生成本周周报（默认本周一）
python3 -m fiw build-weekly
```

### 定时（cron 示例）

```cron
# 每天 08:00 采集并更新看板
0 8 * * * cd /workspace && . /workspace/.venv/bin/activate && python3 -m fiw collect && python3 -m fiw build-daily

# 每周一 08:00 生成周报并推送
0 8 * * 1 cd /workspace && . /workspace/.venv/bin/activate && python3 -m fiw push-weekly
```

> 推送通道：目前内置 SMTP 邮件与企业微信机器人（可选配置 .env）。
