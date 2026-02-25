"""采集器基类"""

import logging
from abc import ABC, abstractmethod

from src.database.models import RawArticle
from src.config.sources import Source

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """采集器抽象基类"""

    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    async def collect(self, source: Source) -> list[RawArticle]:
        """从单个信息源采集文章

        Args:
            source: 信息源配置

        Returns:
            采集到的文章列表
        """
        ...

    async def collect_batch(self, sources: list[Source]) -> list[RawArticle]:
        """批量采集多个信息源

        Args:
            sources: 信息源列表

        Returns:
            所有采集到的文章
        """
        all_articles = []
        for source in sources:
            try:
                articles = await self.collect(source)
                all_articles.extend(articles)
                logger.info(
                    "[%s] %s: 采集到 %d 篇文章",
                    self.name, source.name, len(articles)
                )
            except Exception as e:
                logger.error(
                    "[%s] %s: 采集失败 - %s",
                    self.name, source.name, e
                )
        return all_articles
