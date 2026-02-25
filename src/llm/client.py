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
    OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS,
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
        """初始化OpenAI客户端"""
        if not self.api_key:
            logger.warning("未设置OPENAI_API_KEY，将使用关键词降级方案")
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI客户端初始化成功，模型: %s", self.model)
        except ImportError:
            logger.warning("未安装openai库，将使用关键词降级方案")
        except Exception as e:
            logger.warning("OpenAI客户端初始化失败: %s，将使用降级方案", e)

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
        """批量评估文章重要性

        Args:
            articles: [{"title": ..., "snippet": ..., "source": ..., "index": ...}, ...]

        Returns:
            标注了 importance_score(1-5) 的文章列表
        """
        if not self.is_available:
            return self._fallback_score(articles)

        system_prompt = (
            "你是面向政府领导的AI动态简报编辑。请根据以下标准评估每条新闻的重要性（1-5分）：\n"
            "5分：重大技术突破/重磅政策/行业变革性事件（如GPT-5发布、主要国家AI立法）\n"
            "4分：重要产品发布/关键政策动向/大额融资（如10亿美元以上）\n"
            "3分：值得关注的行业动态（新功能、合作、中等融资）\n"
            "2分：一般性行业新闻（常规更新、小型活动）\n"
            "1分：边缘信息（个人观点、轻微更新）\n\n"
            "评分维度：事件影响力、涉及企业量级、政策关联度、时效性、领导关注度。\n"
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
            "你是面向政府领导的AI动态简报编辑。请将以下英文/中文新闻精编为中文摘要。\n"
            "要求：\n"
            "1. 中文输出，不超过3行（约100-150字）\n"
            "2. 观点鲜明，内容精炼，绝不废话\n"
            "3. 突出关键信息：谁、做了什么、有何影响\n"
            "4. 使用严谨的政府公文风格用语\n"
            "5. 如果原文是英文，翻译为专业的中文表达\n"
            "6. 直接输出摘要内容，不加前缀说明"
        )

        user_prompt = f"来源：{source}\n标题：{title}\n内容：{snippet[:500]}"
        result = self.chat(system_prompt, user_prompt, temperature=0.2)
        return result if result else (snippet[:150] if snippet else title)

    def generate_batch_summaries(self, articles: list[dict]) -> list[str]:
        """批量生成中文精编摘要"""
        if not self.is_available:
            return [a.get("snippet", a.get("title", ""))[:150] for a in articles]

        system_prompt = (
            "你是面向政府领导的AI动态简报编辑。请将以下新闻逐条精编为中文摘要。\n"
            "要求：\n"
            "1. 每条摘要不超过3行（约100-150字），中文输出\n"
            "2. 观点鲜明，内容精炼，政府公文风格\n"
            "3. 突出：谁、做了什么、影响如何\n"
            "4. 输出格式：每条以 '序号:' 开头，后跟摘要内容"
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
            "你是面向政府领导的AI动态简报编辑。请根据本周每日动态，生成一段简洁的周度综述。\n"
            "要求：\n"
            "1. 200-300字，中文\n"
            "2. 概括本周最重要的3-5个趋势或事件\n"
            "3. 政府公文风格，观点鲜明\n"
            "4. 直接输出综述内容"
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
            "你是面向政府领导的AI动态简报编辑。请根据本月各周综述，生成一段月度综合分析。\n"
            "要求：\n"
            "1. 300-500字，中文\n"
            "2. 分析本月AI领域的关键趋势、重大事件、政策动向\n"
            "3. 提出对未来走势的简要研判\n"
            "4. 政府公文风格，内容严谨\n"
            "5. 直接输出综述内容"
        )

        weekly_text = "\n\n".join(
            f"第{i+1}周综述：{s}" for i, s in enumerate(weekly_summaries)
        )
        user_prompt = f"本月各周综述：\n{weekly_text}"
        return self.chat(system_prompt, user_prompt, temperature=0.3)

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
