"""全局配置"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 数据库
DB_PATH = os.getenv("DB_PATH", str(PROJECT_ROOT / "data" / "monitor.db"))

# 输出目录
DOCS_DIR = PROJECT_ROOT / "docs"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# LLM 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MAX_TOKENS = 4096
OPENAI_TEMPERATURE = 0.3

# 采集配置
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "20"))
MAX_PER_DOMAIN = int(os.getenv("MAX_PER_DOMAIN", "2"))
REQUEST_TIMEOUT = 30  # 秒
BROWSER_TIMEOUT = 60  # 秒
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # 指数退避基数（秒）

# 内容提取
MAX_SNIPPET_LENGTH = 500  # 摘要最大字符数
MAX_ARTICLES_PER_SOURCE = 20  # 每个源最多采集文章数

# 筛选配置
RELEVANCE_THRESHOLD = 0.5  # 相关性阈值
DEDUP_SIMILARITY_THRESHOLD = 0.8  # 去重相似度阈值
MIN_IMPORTANCE_FOR_REPORT = 3  # 最低报送评分

# LLM 批量处理
LLM_BATCH_SIZE = 15  # 每批发送给LLM的文章数

# 报告配置
REPORT_TITLE = "人工智能动态简报"
REPORT_SUBTITLE = "AI DAILY INTELLIGENCE BRIEF"

# User-Agent 轮换列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# 分类体系
CATEGORIES = {
    "技术突破": "新模型、新算法、技术里程碑",
    "产品发布": "新产品、功能更新、版本发布",
    "企业动态": "并购、合作、组织调整、战略布局",
    "政策监管": "各国AI政策、法规、标准、治理",
    "投融资": "融资、IPO、估值、市场交易",
    "研究前沿": "学术论文、研究成果、实验突破",
    "行业应用": "AI落地案例、行业解决方案",
    "人才市场": "人才流动、劳动力影响、教育培训",
    "安全伦理": "AI安全、对齐、伦理、风险",
    "芯片与算力": "AI芯片、数据中心、算力基建、半导体",
}

CATEGORY_ORDER = list(CATEGORIES.keys())

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
