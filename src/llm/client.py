"""OpenAI LLM客户端封装

支持：
- gpt-4o-mini（默认，性价比最优）
- gpt-4o（高质量）
- 批量处理
- 重试机制
- 无API Key时的降级方案
"""

import json
import logging
import time
from typing import Optional

from src.config.settings import (
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, OPENAI_MAX_TOKENS,
    OPENAI_TEMPERATURE, MAX_RETRIES, RETRY_BACKOFF
)

logger = logging.getLogger(__name__)

# AI相关关键词列表（降级方案使用）
AI_KEYWORDS = [
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "large language model", "llm", "gpt",
    "transformer", "generative ai", "gen ai", "genai",
    "computer vision", "natural language processing", "nlp",
    "reinforcement learning", "ai model", "ai system",
    "ai safety", "ai alignment", "ai regulation", "ai policy",
    "ai chip", "gpu", "tpu", "ai accelerator",
    "openai", "anthropic", "deepmind", "meta ai",
    "chatgpt", "claude", "gemini", "copilot",
    "ai agent", "autonomous", "robotics",
    "foundation model", "multimodal", "diffusion model",
    "人工智能", "机器学习", "深度学习", "大语言模型", "大模型",
    "生成式AI", "神经网络", "智能算法", "AI芯片", "算力",
    "自动驾驶", "智能体", "具身智能",
]


class LLMClient:
    """LLM客户端"""

    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.model = OPENAI_MODEL
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化LLM客户端（支持OpenAI/DeepSeek等兼容接口）"""
        if not self.api_key:
            logger.warning("未设置OPENAI_API_KEY，将使用关键词降级方案")
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=OPENAI_BASE_URL,
            )
            logger.info("LLM客户端初始化成功，接口: %s，模型: %s",
                         OPENAI_BASE_URL, self.model)
        except ImportError:
            logger.warning("未安装openai库，将使用关键词降级方案")
        except Exception as e:
            logger.warning("LLM客户端初始化失败: %s，将使用降级方案", e)

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = OPENAI_TEMPERATURE,
             max_tokens: int = OPENAI_MAX_TOKENS) -> str:
        """发送聊天请求"""
        if not self.is_available:
            return ""

        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                wait = RETRY_BACKOFF ** (attempt + 1)
                logger.warning(
                    "LLM请求失败 (尝试 %d/%d): %s，等待 %ds",
                    attempt + 1, MAX_RETRIES, e, wait
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait)
        logger.error("LLM请求在 %d 次尝试后仍失败", MAX_RETRIES)
        return ""

    def batch_chat(self, system_prompt: str, user_prompts: list[str],
                   temperature: float = OPENAI_TEMPERATURE) -> list[str]:
        """批量聊天请求（逐个调用，带速率控制）"""
        results = []
        for i, prompt in enumerate(user_prompts):
            result = self.chat(system_prompt, prompt, temperature)
            results.append(result)
            # 简单速率控制
            if i < len(user_prompts) - 1:
                time.sleep(0.5)
        return results

    # ─── 业务方法 ────────────────────────────────────────

    def filter_relevance(self, articles: list[dict]) -> list[dict]:
        """批量判断文章AI相关性

        Args:
            articles: [{"title": ..., "snippet": ..., "index": ...}, ...]

        Returns:
            标注了 is_relevant 的文章列表
        """
        if not self.is_available:
            return self._fallback_filter(articles)

        system_prompt = (
            "你是一个AI领域动态筛选专家。你的任务是判断新闻是否与"
            "人工智能(AI)、机器学习、深度学习、大语言模型、AI芯片、"
            "AI政策监管、AI安全、AI应用等领域直接相关。\n"
            "对于每条新闻，回答'是'或'否'。\n"
            "输出格式：每行一个结果，格式为 '序号:是' 或 '序号:否'"
        )

        # 分批处理
        batch_size = 15
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            prompt_lines = []
            for j, art in enumerate(batch):
                idx = i + j + 1
                prompt_lines.append(
                    f"{idx}. 标题：{art['title']}\n   摘要：{art.get('snippet', '')[:200]}"
                )
            user_prompt = "请判断以下新闻是否与AI相关：\n\n" + "\n\n".join(prompt_lines)

            response = self.chat(system_prompt, user_prompt)
            if response:
                self._parse_relevance_response(response, articles, i)
            else:
                # LLM失败时，降级为全部相关
                for art in batch:
                    art["is_relevant"] = True

        return articles

    def classify_articles(self, articles: list[dict]) -> list[dict]:
        """批量分类文章

        Args:
            articles: [{"title": ..., "snippet": ..., "index": ...}, ...]

        Returns:
            标注了 category 的文章列表
        """
        if not self.is_available:
            return self._fallback_classify(articles)

        categories_desc = (
            "可选分类：\n"
            "1. 技术突破 - 新模型、新算法、技术里程碑\n"
            "2. 产品发布 - 新产品、功能更新、版本发布\n"
            "3. 企业动态 - 并购、合作、组织调整、战略布局\n"
            "4. 政策监管 - 各国AI政策、法规、标准、治理\n"
            "5. 投融资 - 融资、IPO、估值、市场交易\n"
            "6. 研究前沿 - 学术论文、研究成果、实验突破\n"
            "7. 行业应用 - AI落地案例、行业解决方案\n"
            "8. 人才市场 - 人才流动、劳动力影响、教育培训\n"
            "9. 安全伦理 - AI安全、对齐、伦理、风险\n"
            "10. 芯片与算力 - AI芯片、数据中心、算力基建、半导体\n"
        )

        system_prompt = (
            "你是一个AI新闻分类专家。根据新闻标题和摘要，将每条新闻分入最合适的一个分类。\n"
            f"{categories_desc}\n"
            "输出格式：每行一个结果，格式为 '序号:分类名称'"
        )

        batch_size = 15
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            prompt_lines = []
            for j, art in enumerate(batch):
                idx = i + j + 1
                prompt_lines.append(
                    f"{idx}. 标题：{art['title']}\n   摘要：{art.get('snippet', '')[:200]}"
                )
            user_prompt = "请对以下新闻进行分类：\n\n" + "\n\n".join(prompt_lines)

            response = self.chat(system_prompt, user_prompt)
            if response:
                self._parse_classification_response(response, articles, i)
            else:
                for art in batch:
                    art.setdefault("category", "企业动态")

        return articles

    def score_importance(self, articles: list[dict]) -> list[dict]:
        """批量评估文章重要性（高层领导视角）

        Args:
            articles: [{"title": ..., "snippet": ..., "source": ..., "index": ...}, ...]

        Returns:
            标注了 importance_score(1-5) 的文章列表
        """
        if not self.is_available:
            return self._fallback_score(articles)

        system_prompt = (
            "你是一位面向国家高层领导的AI动态简报编辑。领导没有技术专业背景，"
            "负责综合事务，但对AI产业有浓厚兴趣。\n\n"
            "请站在领导的角度评估每条新闻的重要性（1-5分）。领导关心的是：\n"
            "- 对国际社会和全球AI格局有广泛影响的事件\n"
            "- 头部企业（OpenAI、Google、NVIDIA、微软、Meta等）的重大战略动作\n"
            "- 标志性的产品发布（必须是业界广泛关注的，不是普通功能更新）\n"
            "- 重大技术突破（必须是行业公认的里程碑，不是普通学术论文）\n"
            "- 权威机构发布的重大行业数据/报告（麦肯锡、高盛等）\n"
            "- 重要人物的关键言论（马斯克、奥特曼、黄仁勋等）\n"
            "- 主要国家的AI政策/法案（美国行政令、欧盟AI法案、出口管制等）\n"
            "- 大额投融资（10亿美元以上）或重大并购\n\n"
            "评分标准（严格执行，宁缺毋滥）：\n"
            "5分：改变行业格局的重大事件（如GPT新一代发布、主要国家AI立法、百亿级交易）\n"
            "4分：业界广泛关注的重要事件（头部企业重大发布、关键人物重要表态、大额融资）\n"
            "3分：值得领导了解的行业动态（中等规模事件、区域性政策、行业趋势）\n"
            "2分：一般性行业新闻（常规更新、小型合作、普通研究成果）\n"
            "1分：不值得领导关注（纯学术论文、个别技术细节、小型活动、招聘信息）\n\n"
            "注意：普通学术论文、个别算法改进、小型产品更新一律评为1-2分。\n"
            "只有引起业界广泛关注的才给3分以上。\n"
            "输出格式：每行一个结果，格式为 '序号:分数'"
        )

        batch_size = 15
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            prompt_lines = []
            for j, art in enumerate(batch):
                idx = i + j + 1
                prompt_lines.append(
                    f"{idx}. [{art.get('source', '')}] {art['title']}\n"
                    f"   摘要：{art.get('snippet', '')[:200]}"
                )
            user_prompt = "请评估以下新闻的重要性：\n\n" + "\n\n".join(prompt_lines)

            response = self.chat(system_prompt, user_prompt)
            if response:
                self._parse_score_response(response, articles, i)
            else:
                for art in batch:
                    art.setdefault("importance_score", 3)

        return articles

    def generate_summary(self, title: str, snippet: str,
                         source: str = "") -> str:
        """生成单条新闻的中文精编摘要"""
        if not self.is_available:
            return snippet[:150] if snippet else title

        system_prompt = (
            "你是面向国家高层领导的AI动态简报编辑。请将以下新闻精编为'标题+摘要'格式。\n\n"
            "【输出格式】\n"
            "第一行为标题，第二行起为摘要正文（2-3行，约100-150字）。\n\n"
            "【标题撰写规则——最重要】\n"
            "标题必须是一句包含核心结论的陈述句，要求：\n"
            "- 直接写明关键数据（金额、百分比、排名等具体数字）\n"
            "- 直接写明核心结论（是什么、做了什么、结果如何）\n"
            "- 让领导只看标题就能抓住事件本质\n"
            "- 标题长度30-60字\n"
            "正确示范：'英伟达2026财年营收1305亿美元同比增长114%，数据中心业务占比超80%'\n"
            "正确示范：'谷歌发布Gemini 3.1 Pro，ARC-AGI-2测试得分77.1%超越GPT-5.2'\n"
            "正确示范：'Anthropic完成300亿美元G轮融资，估值达3800亿美元创AI行业纪录'\n"
            "错误示范：'英伟达公布2026财年第四季度及全年财务业绩'（没有结论）\n"
            "错误示范：'谷歌发布新一代旗舰模型'（没有具体信息）\n\n"
            "【文风铁律】\n"
            "- 严谨、正式、平实，参照新华社通稿措辞\n"
            "- 禁止感叹号、问号、省略号\n"
            "- 禁止标题党、网络用语、口语化表达\n"
            "- 直接输出，不加前缀说明"
        )

        user_prompt = f"来源：{source}\n标题：{title}\n内容：{snippet[:500]}"
        result = self.chat(system_prompt, user_prompt, temperature=0.2)
        return result if result else (snippet[:150] if snippet else title)

    def generate_batch_summaries(self, articles: list[dict]) -> list[str]:
        """批量生成中文精编摘要"""
        if not self.is_available:
            return [a.get("snippet", a.get("title", ""))[:150] for a in articles]

        system_prompt = (
            "你是面向国家高层领导的AI动态简报编辑。请将以下新闻逐条精编。\n\n"
            "【输出格式】\n"
            "每条格式为：'序号: 【标题】摘要正文'\n"
            "- 标题用【】括起，30-60字，必须包含核心结论和关键数据\n"
            "- 摘要正文紧跟标题后，2-3行，约100-150字\n\n"
            "【标题撰写规则——最重要】\n"
            "标题必须让领导只看这一句就能抓住事件本质：\n"
            "- 必须包含具体数据（金额、百分比、排名等，如有）\n"
            "- 必须包含核心结论（是什么、做了什么、结果如何）\n"
            "- 正确：'英伟达2026财年营收1305亿美元同比增114%，数据中心占比超80%'\n"
            "- 正确：'Anthropic完成300亿美元融资，估值3800亿美元创AI纪录'\n"
            "- 错误：'英伟达公布财务业绩'（无数据无结论）\n"
            "- 错误：'Anthropic完成新一轮融资'（无金额无估值）\n\n"
            "【文风铁律】\n"
            "- 严谨、正式、平实，参照新华社通稿\n"
            "- 禁止感叹号、标题党、网络用语、口语化"
        )

        results = [""] * len(articles)
        batch_size = 10
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            prompt_lines = []
            for j, art in enumerate(batch):
                idx = i + j + 1
                prompt_lines.append(
                    f"{idx}. [{art.get('source', '')}] {art['title']}\n"
                    f"   内容：{art.get('snippet', '')[:300]}"
                )
            user_prompt = "请对以下新闻逐条生成精编中文摘要：\n\n" + "\n\n".join(prompt_lines)
            response = self.chat(system_prompt, user_prompt, temperature=0.2)

            if response:
                self._parse_summary_response(response, results, i, batch)
            else:
                for j, art in enumerate(batch):
                    results[i + j] = art.get("snippet", art.get("title", ""))[:150]

        return results

    def generate_weekly_overview(self, daily_summaries: list[dict]) -> str:
        """生成每周总结概述"""
        if not self.is_available:
            return "本周AI领域动态汇总如下。"

        system_prompt = (
            "你是面向国家高层领导的AI动态简报编辑。请生成一段简洁的周度综述。\n"
            "要求：\n"
            "1. 200-300字，中文\n"
            "2. 概括本周最重要的3-5个趋势或事件\n"
            "3. 语言严谨、正式、平实，参照政府公文和新华社通稿风格\n"
            "4. 直接输出综述内容\n"
            "5. 禁止感叹号、夸张修辞、标题党词汇、网络用语"
        )

        articles_text = "\n".join(
            f"- [{d.get('date', '')}] {d.get('title', '')}: {d.get('summary', '')[:100]}"
            for d in daily_summaries[:50]  # 限制输入量
        )
        user_prompt = f"本周动态列表：\n{articles_text}"
        return self.chat(system_prompt, user_prompt, temperature=0.3)

    def generate_monthly_overview(self, weekly_summaries: list[str]) -> str:
        """生成月度综述"""
        if not self.is_available:
            return "本月AI领域动态综述如下。"

        system_prompt = (
            "你是面向国家高层领导的AI动态简报编辑。请生成一段月度综合分析。\n"
            "要求：\n"
            "1. 300-500字，中文\n"
            "2. 分析本月AI领域的关键趋势、重大事件、政策动向\n"
            "3. 提出对未来走势的简要研判\n"
            "4. 语言严谨、正式、平实，参照政府公文和新华社通稿风格\n"
            "5. 直接输出综述内容\n"
            "6. 禁止感叹号、夸张修辞、标题党词汇、网络用语"
        )

        weekly_text = "\n\n".join(
            f"第{i+1}周综述：{s}" for i, s in enumerate(weekly_summaries)
        )
        user_prompt = f"本月各周综述：\n{weekly_text}"
        return self.chat(system_prompt, user_prompt, temperature=0.3)

    # ─── 精选报送筛选 ────────────────────────────────────

    def screen_elite_picks(self, articles: list[dict],
                            max_per_category: int = 5) -> list[dict]:
        """精选报送筛选 — 模拟高层领导的信息筛选思维

        从已评分文章中，按照领导视角进行二次精筛，
        每个分类原则上不超过5条，除非确实影响力巨大。

        Args:
            articles: [{"title_zh":..., "summary_zh":..., "category":...,
                        "importance_score":..., "source_name":..., ...}]
            max_per_category: 每类最大条数

        Returns:
            标注了 is_elite(bool) 的文章列表
        """
        if not self.is_available:
            return self._fallback_elite(articles, max_per_category)

        system_prompt = (
            "你是一位服务国家高层领导的AI动态简报总编辑。\n"
            "领导没有技术专业背景，处理综合事务，但对AI高度关注。\n\n"
            "你的任务：从以下已筛选的AI动态中，精选出真正值得领导阅读的条目。\n\n"
            "领导的关注逻辑（按优先级）：\n"
            "1️⃣ 重点国家AI政策/法案 — 美国、欧盟、英国、中国等重大AI立法或行政令\n"
            "2️⃣ 重大企业动作 — OpenAI/Google/NVIDIA等头部企业的战略级动作（非普通更新）\n"
            "3️⃣ 标志性产品发布 — 引起全行业关注的里程碑式发布（非小版本迭代）\n"
            "4️⃣ 行业关键数据/报告 — 麦肯锡、高盛等权威机构的重大行业报告\n"
            "5️⃣ 重要人物言论 — 马斯克、奥特曼、黄仁勋等的关键公开表态\n"
            "6️⃣ 大额投融资/并购 — 10亿美元以上的标志性交易\n"
            "7️⃣ 重大技术突破 — 必须是业界公认的里程碑（非普通论文或算法改进）\n"
            "8️⃣ AI安全/伦理重大事件 — 影响广泛的安全事件或伦理争议\n\n"
            "筛选原则：\n"
            "- 宁缺毋滥，每个分类原则上不超过5条\n"
            "- 普通学术论文、个别技术细节、小型活动一律不入选\n"
            "- 只留下'领导看了会觉得值得了解'的内容\n"
            "- 如果某条确实影响力巨大，可以突破5条限制\n\n"
            "输出格式：每行输出入选条目的序号，格式为 '序号:入选'\n"
            "不入选的不用输出。"
        )

        # 分批处理
        batch_size = 20
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            prompt_lines = []
            for j, art in enumerate(batch):
                idx = i + j + 1
                prompt_lines.append(
                    f"{idx}. [{art.get('category', '')}] [{art.get('source_name', '')}] "
                    f"{art.get('title_zh', '')}\n"
                    f"   摘要：{art.get('summary_zh', '')[:150]}"
                )
            user_prompt = (
                f"请从以下{len(batch)}条动态中精选出值得领导阅读的条目：\n\n"
                + "\n\n".join(prompt_lines)
            )

            response = self.chat(system_prompt, user_prompt)
            if response:
                self._parse_elite_response(response, articles, i)
            else:
                # LLM失败时，降级为按分数筛选
                for art in batch:
                    art.setdefault("is_elite", art.get("importance_score", 0) >= 4)

        return articles

    def _parse_elite_response(self, response: str, articles: list[dict],
                               offset: int):
        """解析精选筛选响应"""
        elite_indices = set()
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            for sep in [":", "：", ".", "、"]:
                if sep in line:
                    prefix = line.split(sep, 1)[0].strip()
                    try:
                        idx = int(prefix) - 1
                        if "入选" in line or "选" in line or idx >= 0:
                            elite_indices.add(idx)
                        break
                    except ValueError:
                        continue

        for idx in elite_indices:
            if 0 <= idx < len(articles):
                articles[idx]["is_elite"] = True

    def _fallback_elite(self, articles: list[dict],
                         max_per_category: int) -> list[dict]:
        """精选降级方案：按分数+规则筛选"""
        from collections import Counter
        cat_count: dict[str, int] = Counter()

        # 按分数降序排列
        sorted_arts = sorted(
            enumerate(articles),
            key=lambda x: x[1].get("importance_score", 0),
            reverse=True
        )

        for idx, art in sorted_arts:
            cat = art.get("category", "")
            score = art.get("importance_score", 0)
            if score >= 4 and cat_count[cat] < max_per_category:
                art["is_elite"] = True
                cat_count[cat] += 1
            elif score >= 5:  # 5分的即使超限也入选
                art["is_elite"] = True
                cat_count[cat] += 1

        return articles

    # ─── 降级方案 ────────────────────────────────────────

    def _fallback_filter(self, articles: list[dict]) -> list[dict]:
        """关键词匹配降级方案"""
        for art in articles:
            text = f"{art.get('title', '')} {art.get('snippet', '')}".lower()
            art["is_relevant"] = any(kw in text for kw in AI_KEYWORDS)
        return articles

    def _fallback_classify(self, articles: list[dict]) -> list[dict]:
        """基于关键词的分类降级方案"""
        classification_keywords = {
            "技术突破": ["breakthrough", "new model", "state-of-the-art", "benchmark", "突破", "里程碑"],
            "产品发布": ["launch", "release", "announce", "available", "发布", "上线", "推出"],
            "企业动态": ["acquire", "merger", "partnership", "hire", "收购", "合作", "战略"],
            "政策监管": ["regulation", "policy", "law", "act", "govern", "政策", "监管", "法规"],
            "投融资": ["funding", "invest", "ipo", "valuation", "融资", "投资", "估值"],
            "研究前沿": ["research", "paper", "study", "arxiv", "论文", "研究"],
            "行业应用": ["deploy", "implement", "use case", "industry", "应用", "落地"],
            "人才市场": ["talent", "hire", "workforce", "job", "人才", "就业"],
            "安全伦理": ["safety", "alignment", "ethics", "risk", "bias", "安全", "伦理"],
            "芯片与算力": ["chip", "gpu", "semiconductor", "compute", "芯片", "算力", "半导体"],
        }
        for art in articles:
            text = f"{art.get('title', '')} {art.get('snippet', '')}".lower()
            best_cat = "企业动态"
            best_count = 0
            for cat, keywords in classification_keywords.items():
                count = sum(1 for kw in keywords if kw in text)
                if count > best_count:
                    best_count = count
                    best_cat = cat
            art["category"] = best_cat
        return articles

    def _fallback_score(self, articles: list[dict]) -> list[dict]:
        """基于规则的评分降级方案"""
        high_priority_sources = [
            "openai", "google", "meta", "microsoft", "apple", "nvidia",
            "anthropic", "白宫", "ostp", "nist", "eu", "欧盟",
        ]
        for art in articles:
            score = 3  # 默认分数
            source = art.get("source", "").lower()
            title = art.get("title", "").lower()

            # 来自顶级企业/政府 +1
            if any(s in source for s in high_priority_sources):
                score += 1

            # 包含重大关键词 +1
            major_keywords = ["breakthrough", "regulation", "ban", "billion",
                              "launch", "突破", "发布", "禁止", "亿"]
            if any(kw in title for kw in major_keywords):
                score += 1

            art["importance_score"] = min(score, 5)
        return articles

    # ─── 解析响应 ────────────────────────────────────────

    def _parse_relevance_response(self, response: str, articles: list[dict],
                                   offset: int):
        """解析相关性判断响应"""
        for line in response.strip().split("\n"):
            line = line.strip()
            if ":" in line or "：" in line:
                sep = ":" if ":" in line else "："
                parts = line.split(sep, 1)
                try:
                    idx = int(parts[0].strip().rstrip(".、)）")) - 1
                    is_yes = "是" in parts[1] or "yes" in parts[1].lower()
                    if 0 <= idx < len(articles):
                        articles[idx]["is_relevant"] = is_yes
                except (ValueError, IndexError):
                    continue

    def _parse_classification_response(self, response: str,
                                        articles: list[dict], offset: int):
        """解析分类响应"""
        from src.config.settings import CATEGORIES
        valid_cats = set(CATEGORIES.keys())
        for line in response.strip().split("\n"):
            line = line.strip()
            if ":" in line or "：" in line:
                sep = ":" if ":" in line else "："
                parts = line.split(sep, 1)
                try:
                    idx = int(parts[0].strip().rstrip(".、)）")) - 1
                    cat = parts[1].strip()
                    if cat in valid_cats and 0 <= idx < len(articles):
                        articles[idx]["category"] = cat
                except (ValueError, IndexError):
                    continue

    def _parse_score_response(self, response: str, articles: list[dict],
                               offset: int):
        """解析评分响应"""
        for line in response.strip().split("\n"):
            line = line.strip()
            if ":" in line or "：" in line:
                sep = ":" if ":" in line else "："
                parts = line.split(sep, 1)
                try:
                    idx = int(parts[0].strip().rstrip(".、)）")) - 1
                    score = int(parts[1].strip().rstrip("分★"))
                    score = max(1, min(5, score))
                    if 0 <= idx < len(articles):
                        articles[idx]["importance_score"] = score
                except (ValueError, IndexError):
                    continue

    def _parse_summary_response(self, response: str, results: list[str],
                                 offset: int, batch: list[dict]):
        """解析摘要响应"""
        current_idx = None
        current_text = []

        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # 检查是否是新的序号开头
            parsed_idx = None
            for sep in [":", "：", ".", "、"]:
                if sep in line:
                    prefix = line.split(sep, 1)[0].strip()
                    try:
                        parsed_idx = int(prefix) - 1
                        line_content = line.split(sep, 1)[1].strip()
                        break
                    except ValueError:
                        continue

            if parsed_idx is not None and 0 <= parsed_idx < len(results):
                # 保存上一条
                if current_idx is not None and 0 <= current_idx < len(results):
                    results[current_idx] = "\n".join(current_text)
                current_idx = parsed_idx
                current_text = [line_content] if line_content else []
            elif current_idx is not None:
                current_text.append(line)

        # 保存最后一条
        if current_idx is not None and 0 <= current_idx < len(results):
            results[current_idx] = "\n".join(current_text)

        # 填充空值
        for i in range(offset, min(offset + len(batch), len(results))):
            if not results[i]:
                art = batch[i - offset]
                results[i] = art.get("snippet", art.get("title", ""))[:150]
