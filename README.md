## Future-Industry-Weekly-Post

一个“未来产业周度要闻”的自动采集、重要性分析、可视化看板与周报PDF生成系统。

### 你将得到什么

- **每天 08:00 自动采集**：国内外科技企业 / 学术机构 / 国家政策 / 投融资等动态（RSS + GDELT 全网检索为主）
- **采集结果全部落地 CSV**：可追溯、可审计、可二次分析
- **每日 HTML 看板**：分“精简版 / 完整版”，支持筛选与搜索
- **每周一 08:00 自动生成周报 PDF**：版式与栏目对标你提供的样例（第一版已实现，后续可继续逼近字体/间距/栏目映射）
- **GitHub Pages 发布**：每日构建静态站点到 `site/` 并自动部署，方便对外分享

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

# 生成静态站点（用于 GitHub Pages）
python3 -m fiw build-site --max-days 60
```

### 定时（cron 示例）

```cron
# 每天 08:00 采集并更新看板
0 8 * * * cd /workspace && . /workspace/.venv/bin/activate && python3 -m fiw collect && python3 -m fiw build-daily

# 每周一 08:00 生成周报并推送
0 8 * * 1 cd /workspace && . /workspace/.venv/bin/activate && python3 -m fiw push-weekly
```

> 推送通道：目前内置 SMTP 邮件与企业微信机器人（可选配置 .env）。

### GitHub Pages（推荐：全自动分享）

仓库已内置工作流：
- `.github/workflows/daily.yml`：每天 08:00（北京时间）采集 + 构建 `site/` 并推送到 `gh-pages` 分支（用于 Pages 发布）
- `.github/workflows/weekly.yml`：周一 08:00（北京时间）生成周报 PDF，并可通过 SMTP 邮件发送

你需要在仓库 `Settings -> Secrets and variables -> Actions` 配置（发邮件才需要）：`FIW_SMTP_HOST/FIW_SMTP_PORT/FIW_SMTP_USER/FIW_SMTP_PASS/FIW_SMTP_FROM`，以及可选 `FIW_DEEPSEEK_API_KEY`。

Pages 设置方式（适配你看到的老界面）：
- `Settings -> Pages`
- `Source` 选择 **Deploy from a branch**
- `Branch` 选择 **gh-pages**，目录选择 **/ (root)**  
首次需要先跑一次 `Daily Collect, Build Site & Publish Pages (gh-pages)` 工作流来生成 `gh-pages` 分支。
