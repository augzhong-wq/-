"""精编摘要生成器

对入选动态用LLM生成中文精编摘要。
要求：
- 中文输出，不超过3行（约100-150字）
- 观点鲜明，内容精炼
- 政府公文风格
"""

import logging
from src.database.models import CuratedArticle
from src.llm.client import LLMClient

logger = logging.getLogger(__name__)


class Summarizer:
    """精编摘要生成器"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate_summaries(
        self, articles: list[CuratedArticle]
    ) -> list[CuratedArticle]:
        """为文章列表生成精编中文摘要

        Args:
            articles: 入选简报的文章列表

        Returns:
            带有精编摘要的文章列表
        """
        if not articles:
            return []

        logger.info("开始为 %d 篇文章生成精编摘要...", len(articles))

        # 准备批量输入
        article_dicts = []
        for art in articles:
            article_dicts.append({
                "title": art.title_zh,
                "snippet": art.summary_zh,
                "source": art.source_name,
            })

        # 批量生成摘要
        summaries = self.llm.generate_batch_summaries(article_dicts)

        # 更新文章标题和摘要
        for i, art in enumerate(articles):
            if i < len(summaries) and summaries[i]:
                text = summaries[i].strip()

                # 尝试从LLM输出中分离标题和摘要
                title, body = self._split_title_and_body(text)

                if title:
                    art.title_zh = title
                    art.summary_zh = body if body else text
                else:
                    # 无法分离时，用第一句做标题，其余做摘要
                    art.title_zh = self._extract_title_from_summary(
                        text, art.title_zh
                    )
                    art.summary_zh = text

        logger.info("精编摘要生成完成")
        return articles

    def generate_highlights(
        self, articles: list[CuratedArticle], count: int = 5
    ) -> list[str]:
        """生成本期要点（3-5条核心摘要）

        Args:
            articles: 入选简报的文章（已按重要性排序）
            count: 要点数量

        Returns:
            要点列表
        """
        if not articles:
            return []

        top_articles = sorted(
            articles, key=lambda a: a.importance_score, reverse=True
        )[:count]

        if not self.llm.is_available:
            # 降级：直接使用标题
            return [art.title_zh for art in top_articles]

        system_prompt = (
            "你是面向国家高层领导的AI动态简报编辑。请根据以下重要新闻，"
            "提炼出3-5条'本期要点'。\n"
            "要求：\n"
            "1. 每条要点一句话，20-40字\n"
            "2. 语言严谨、正式、平实，参照新华社通稿风格\n"
            "3. 每条以'▸'开头\n"
            "4. 直接输出要点，不加其他说明\n"
            "5. 禁止使用感叹号、网络用语、夸张修辞、标题党词汇\n"
            "6. 正确示范：'▸ 谷歌发布Gemini 3.1 Pro模型，推理能力显著提升'\n"
            "7. 错误示范：'▸ 谷歌重磅发布最强模型！性能炸裂'"
        )

        articles_text = "\n".join(
            f"{i+1}. [{art.source_name}] {art.title_zh}: {art.summary_zh[:100]}"
            for i, art in enumerate(top_articles)
        )

        response = self.llm.chat(system_prompt, articles_text, temperature=0.2)
        if response:
            highlights = [
                line.strip()
                for line in response.strip().split("\n")
                if line.strip() and len(line.strip()) > 5
            ]
            return highlights[:count]

        return [art.title_zh for art in top_articles]

    @staticmethod
    def _split_title_and_body(text: str) -> tuple[str, str]:
        """从LLM输出中分离标题和摘要正文

        支持的格式：
        - 【标题】摘要正文
        - 标题\n摘要正文（第一行为标题）
        """
        text = text.strip()

        # 格式1: 【标题】摘要
        if "【" in text and "】" in text:
            start = text.index("【") + 1
            end = text.index("】")
            title = text[start:end].strip()
            body = text[end + 1:].strip()
            if title and len(title) >= 10:
                return title, body

        # 格式2: 第一行为标题（如果第一行30-80字且不含句号结尾）
        lines = text.split("\n", 1)
        if len(lines) >= 2:
            first_line = lines[0].strip()
            rest = lines[1].strip()
            if 10 <= len(first_line) <= 100 and not first_line.endswith("。"):
                return first_line, rest

        # 格式3: 用第一个句号分割
        for sep in ["。", "；"]:
            if sep in text:
                parts = text.split(sep, 1)
                title_candidate = parts[0].strip()
                if 10 <= len(title_candidate) <= 100:
                    return title_candidate, text
                break

        return "", text

    @staticmethod
    def _is_mostly_english(text: str) -> bool:
        """判断文本是否主要是英文"""
        if not text:
            return False
        ascii_count = sum(1 for c in text if ord(c) < 128)
        return ascii_count / len(text) > 0.7

    @staticmethod
    def _extract_title_from_summary(summary: str, original_title: str) -> str:
        """从摘要中提取中文标题"""
        # 取摘要的第一句作为标题
        for sep in ["。", "，", "；", "\n"]:
            if sep in summary:
                first_sentence = summary.split(sep)[0].strip()
                if 10 <= len(first_sentence) <= 50:
                    return first_sentence
        # 如果提取失败，截取前30字
        if len(summary) > 10:
            return summary[:30] + "..."
        return original_title
